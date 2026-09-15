#!/usr/bin/env python3
"""Convert a real Legistar instance into the schemaGov meetings profile.

Legistar (Granicus) runs the legislative record for a large share of North American
cities. Its Web API is public and unauthenticated for most clients.

    python3 tools/adapters/legistar.py --client seattle --meetings 8 \
        --out examples/pilot-seattle-meetings

The API is shaped as one call per meeting for agenda items and one per item for votes,
so --meetings governs request volume. Unmapped values are reported rather than guessed.
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://webapi.legistar.com/v1"
UA = "schemaGov-adapter/1.0 (+https://schema.govfresh.com)"

# Legistar vote vocabularies are configured per client, so these are the common values
# rather than a closed set. Anything unrecognised is reported, never guessed.
VOTE_MAP = {
    "in favor": "yes", "yea": "yes", "yes": "yes", "aye": "yes", "for": "yes",
    "opposed": "no", "nay": "no", "no": "no", "against": "no",
    "abstain": "abstain", "abstained": "abstain", "present": "abstain",
    "absent": "absent", "not present": "absent",
    "excused": "excused", "recused": "excused", "conflict": "excused",
    "non voting": "notVoting", "not voting": "notVoting",
    # Legistar clients embed qualifiers in the label itself.
    "absent nv": "absent", "absent not voting": "absent",
}


def normalise(label):
    """Vote and action labels carry punctuation and parenthetical qualifiers that vary
    by client - 'Absent(NV)', 'Heard in Committee'. Normalise before matching so the
    maps stay readable instead of accumulating spelling variants."""
    return re.sub(r"[^a-z0-9]+", " ", str(label).lower()).strip()

# Legistar action names are also client-configured.
ACTION_MAP = {
    "pass": "adopted", "passed": "adopted", "adopt": "adopted", "adopted": "adopted",
    "approve": "adopted", "approved": "adopted", "confirm": "adopted",
    "fail": "rejected", "failed": "rejected", "reject": "rejected", "deny": "rejected",
    "defer": "deferred", "postpone": "deferred", "hold": "deferred",
    "table": "deferred", "continue": "deferred",
    "refer": "referred", "referred": "referred", "recommend": "referred",
    "amend": "amended", "amended": "amended",
    "withdraw": "withdrawn", "withdrawn": "withdrawn",
    "file": "received", "received": "received", "presented": "received",
    "discuss": "received", "heard": "received",
    "no action": "noAction",
    # Seen in real Seattle data on the first run.
    "confirm": "adopted", "confirmed": "adopted",
    "discussed": "received", "heard in committee": "received",
    "heard": "received", "briefed": "received",
}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def local_id(v):
    return {"@type": "PropertyValue", "propertyID": "local:legistar", "value": str(v)}


def combine_datetime(date, time, tz_offset, notes):
    """Legistar splits the date from the time and carries no timezone on either.

    EventDate is '2026-09-11T00:00:00' and EventTime is '9:30 AM'. A meeting time
    without an offset is ambiguous, so the publisher's offset has to be supplied from
    outside the API - here via --utc-offset, which a real deployment would take from
    the jurisdiction's gs:timeZone.
    """
    if not date:
        return None
    day = date[:10]
    if not time:
        notes["meeting has a date but no time"] += 1
        return day
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]\.?\s*$", str(time))
    if not m:
        notes[f"unparsed EventTime '{time}'"] += 1
        return day
    hh, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == "p" and hh != 12:
        hh += 12
    if ap == "a" and hh == 12:
        hh = 0
    return f"{day}T{hh:02d}:{mm}:00{tz_offset}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True)
    ap.add_argument("--meetings", type=int, default=8)
    ap.add_argument("--utc-offset", default="-07:00",
                    help="Offset for the publisher's local time; Legistar carries none.")
    ap.add_argument("--base")
    ap.add_argument("--out", default="examples/pilot-legistar")
    args = ap.parse_args()

    client = args.client
    base = (args.base or f"https://{client}.legistar.com/id").rstrip("/")
    gaps, notes = defaultdict(int), defaultdict(int)

    bodies = {b["BodyId"]: b for b in fetch(f"{API}/{client}/Bodies")}
    q = urllib.parse.quote(f"EventDate lt datetime'2026-09-01'")
    events = fetch(f"{API}/{client}/Events?$top={args.meetings}"
                   f"&$orderby=EventDate desc&$filter={q}".replace(" ", "%20"))

    orgs, people, meetings, legislation = {}, {}, [], {}

    # Legistar publishes no jurisdiction metadata at all, so a minimal one is derived
    # from the client name. It is marked local: because it is inferred, not sourced.
    juris_id = f"{base}/jurisdiction/{client}"
    jurisdiction = {
        "@id": juris_id, "@type": "City",
        "name": client.replace("-", " ").title(),
        "governmentLevel": "municipal",
        "identifier": [{"@type": "PropertyValue",
                        "propertyID": "local:legistar-client", "value": client}],
    }
    notes["jurisdiction derived from the client name; Legistar publishes none"] += 1

    for ev in events:
        body = bodies.get(ev.get("EventBodyId"), {})
        oid = f"{base}/organization/{slug(ev.get('EventBodyName') or ev.get('EventBodyId'))}"
        orgs[oid] = {
            "@id": oid, "@type": "GovernmentOrganization",
            "name": ev.get("EventBodyName") or "Unknown body",
            "identifier": [local_id(ev.get("EventBodyId"))],
            "organizationClassification":
                "legislature" if "council" in (ev.get("EventBodyName") or "").lower()
                else "committee",
            "areaServed": {"@id": juris_id, "name": jurisdiction["name"]},
        }

        start = combine_datetime(ev.get("EventDate"), ev.get("EventTime"),
                                 args.utc_offset, notes)
        cancelled = (ev.get("EventAgendaStatusName") == "Cancelled"
                     or ev.get("EventMinutesStatusName") == "Cancelled"
                     or "cancel" in (ev.get("EventComment") or "").lower())

        meeting = {
            "@id": f"{base}/meeting/{ev['EventId']}",
            "@type": "Meeting",
            "name": f"{ev.get('EventBodyName')}, {(ev.get('EventDate') or '')[:10]}",
            "identifier": [local_id(ev["EventId"])],
            "organizer": {"@id": oid, "name": orgs[oid]["name"]},
            "eventStatus": "EventCancelled" if cancelled else "EventScheduled",
        }
        if start:
            meeting["startDate"] = start
        if ev.get("EventComment"):
            meeting["description"] = ev["EventComment"]
        if ev.get("EventInSiteURL"):
            meeting["url"] = ev["EventInSiteURL"]
        if ev.get("EventAgendaFile"):
            meeting["agendaDocument"] = ev["EventAgendaFile"]
        if ev.get("EventMinutesFile"):
            meeting["minutes"] = ev["EventMinutesFile"]
        if ev.get("EventVideoPath"):
            meeting["recording"] = [{"@type": "VideoObject",
                                     "name": "Meeting video",
                                     "contentUrl": ev["EventVideoPath"]}]
        if ev.get("EventLocation"):
            # A multi-line address string, not a facility reference. _core Facility
            # expects an entity; there is nothing here to resolve one from.
            notes["EventLocation is free text, not a resolvable facility"] += 1

        items = []
        try:
            raw_items = fetch(f"{API}/{client}/Events/{ev['EventId']}/EventItems")
        except Exception:
            raw_items = []

        for idx, it in enumerate(raw_items, start=1):
            title = (it.get("EventItemTitle") or it.get("EventItemMatterName")
                     or it.get("EventItemActionText") or "Untitled item")
            agenda_no = (it.get("EventItemAgendaNumber") or "").strip() or None

            item = {
                "@type": "AgendaItem",
                "@id": f"{base}/meeting/{ev['EventId']}/item/{it['EventItemId']}",
                "name": re.sub(r"\s+", " ", str(title))[:300],
                # Legistar agenda numbers are strings like "3.", "A.", "2a." - not
                # integers. schema:position ranges over Integer OR Text.
                "position": agenda_no or idx,
            }

            action = normalise(it.get("EventItemActionName")) if it.get("EventItemActionName") else ""
            if action:
                mapped = ACTION_MAP.get(action)
                if mapped:
                    item["result"] = mapped
                else:
                    gaps[f"action:{it.get('EventItemActionName')}"] += 1

            # A matter is a piece of legislation; project it into the code profile so
            # the meetings-to-code join is exercised against real data.
            if it.get("EventItemMatterId"):
                lid = f"{base}/legislation/{it['EventItemMatterId']}"
                if lid not in legislation:
                    legislation[lid] = {
                        "@id": lid, "@type": "Legislation",
                        "name": (it.get("EventItemMatterName")
                                 or it.get("EventItemMatterFile") or "Matter"),
                        "legislationIdentifier": it.get("EventItemMatterFile"),
                        "legislationType": "ordinance"
                        if str(it.get("EventItemMatterFile", "")).upper().startswith("CB")
                        else "resolution",
                        "identifier": [local_id(it["EventItemMatterId"])],
                        "legislationJurisdiction": {"@id": juris_id,
                                                    "name": jurisdiction["name"]},
                        "enactedAt": {"@id": meeting["@id"]},
                    }
                item["about"] = [{"@id": lid, "name": legislation[lid]["name"]}]

            try:
                raw_votes = fetch(f"{API}/{client}/EventItems/{it['EventItemId']}/Votes")
            except Exception:
                raw_votes = []

            if raw_votes:
                counts, cast = {}, []
                for v in raw_votes:
                    label = normalise(v.get("VoteValueName"))
                    opt = VOTE_MAP.get(label)
                    if not opt:
                        gaps[f"vote:{v.get('VoteValueName')}"] += 1
                        continue
                    pid = f"{base}/person/{slug(v.get('VotePersonName') or v.get('VotePersonId'))}"
                    people[pid] = {"@id": pid, "@type": "Person",
                                   "name": v.get("VotePersonName") or "Unknown",
                                   "identifier": [local_id(v.get("VotePersonId"))]}
                    counts[opt] = counts.get(opt, 0) + 1
                    cast.append({"@type": "Vote",
                                 "voter": {"@id": pid, "name": people[pid]["name"]},
                                 "option": opt})
                if cast:
                    passed = counts.get("yes", 0) > counts.get("no", 0)
                    item["voteEvent"] = [{
                        "@type": "VoteEvent",
                        "@id": f"{item['@id']}/vote",
                        "name": f"Vote on {item['name'][:80]}",
                        "organizer": {"@id": oid},
                        "result": "passed" if passed else "failed",
                        "count": [{"option": o, "value": n} for o, n in sorted(counts.items())],
                        "vote": cast,
                    }]
                    if item.get("about"):
                        item["voteEvent"][0]["about"] = item["about"]
                    notes["requiredMajority not published by Legistar"] += 1
            items.append(item)

        if items:
            meeting["agendaItem"] = items
        meetings.append(meeting)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    for fname, graph in (("jurisdictions.jsonld", [jurisdiction]),
                         ("organizations.jsonld", list(orgs.values())),
                         ("people.jsonld", list(people.values())),
                         ("meetings.jsonld", meetings),
                         ("code.jsonld", list(legislation.values()))):
        (out / fname).write_text(
            json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")

    print(f"legistar adapter: {client} -> {len(meetings)} meeting(s), "
          f"{sum(len(m.get('agendaItem', [])) for m in meetings)} agenda item(s), "
          f"{len(people)} person(s), {len(legislation)} matter(s)")
    print(f"  written to {out}/")
    if notes:
        print("\n  conversion notes:")
        for k, n in sorted(notes.items(), key=lambda x: -x[1]):
            print(f"    {k:58} {n}x")
    if gaps:
        print("\n  values with no schemaGov mapping:")
        for k, n in sorted(gaps.items(), key=lambda x: -x[1]):
            print(f"    {k:58} {n}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
