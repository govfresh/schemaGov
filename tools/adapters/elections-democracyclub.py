#!/usr/bin/env python3
"""Convert Democracy Club UK election data into the schemaGov elections profile.

Democracy Club publishes every UK election - 42,000 ballots - with the voting system,
seats contested, candidacies, parties and declared results. The UK runs several electoral
systems side by side, which makes it the right test of the profile's claim that
electoralSystem is what lets election data travel.

    python3 tools/adapters/elections-democracyclub.py --date 2024-05-02 --limit 40 \
        --out examples/pilot-uk-elections
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.request
from collections import defaultdict

API = "https://candidates.democracyclub.org.uk/api/next"
UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"

# UK system names -> the profile's ElectoralSystem code list.
SYSTEMS = {
    "FPTP": "fptp",
    "AMS": "mmp",          # Additional Member System is mixed-member proportional
    "STV": "stv",
    "sv": "twoRound",      # Supplementary Vote: a compressed two-round contest
    "SV": "twoRound",
    "PR-CL": "partyList",
    "BV": "blockVote",
}

ELECTION_KIND = {
    "parl": "general", "gla": "general", "nia": "general", "sp": "general",
    "senedd": "general", "naw": "general", "local": "general", "mayor": "general",
    "pcc": "general", "europarl": "general", "ref": "referendum",
}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2024-05-02")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default="examples/pilot-uk-elections")
    args = ap.parse_args()

    gaps, notes = defaultdict(int), defaultdict(int)
    base = "https://candidates.democracyclub.org.uk/id"

    ballots, url = [], f"{API}/ballots/?election_date={args.date}&limit=100"
    while url and len(ballots) < args.limit:
        page = fetch(url)
        ballots.extend(page.get("results", []))
        url = page.get("next")
    ballots = ballots[: args.limit]

    juris_id = f"{base}/jurisdiction/gb"
    jurisdiction = {"@id": juris_id, "@type": "Country", "name": "United Kingdom",
                    "governmentLevel": "national",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "iso3166-1-alpha2", "value": "GB"}]}
    admin_id = f"{base}/organization/returning-officers"
    admin = {"@id": admin_id, "@type": "GovernmentOrganization",
             "name": "UK returning officers",
             "description": "Elections in the UK are administered locally by returning "
                            "officers; Democracy Club aggregates their declarations "
                            "without naming a single administering body.",
             "identifier": [{"@type": "PropertyValue", "propertyID": "local:democracyclub",
                             "value": "returning-officers"}],
             "organizationClassification": "agency",
             "areaServed": {"@id": juris_id, "name": "United Kingdom"}}

    elections, contests, posts, parties, people = {}, [], {}, {}, {}

    for b in ballots:
        bid = b.get("ballot_paper_id")
        if not bid:
            continue
        el = b.get("election") or {}
        eid = el.get("election_id")
        if not eid:
            continue

        if eid not in elections:
            kind = ELECTION_KIND.get(eid.split(".")[0])
            if not kind:
                gaps[f"electionType:{eid.split('.')[0]}"] += 1
                kind = "general"
            elections[eid] = {
                "@id": f"{base}/election/{slug(eid)}", "@type": "Election",
                "name": el.get("name") or eid,
                "electionDate": args.date,
                "electionType": kind,
                "electionStatus": "completed",
                "administeredBy": {"@id": admin_id, "name": admin["name"]},
                "jurisdiction": {"@id": juris_id, "name": "United Kingdom"},
                "identifier": [{"@type": "PropertyValue",
                                "propertyID": "local:democracyclub", "value": eid}],
                "contest": [],
            }

        post = b.get("post") or {}
        post_id = f"{base}/post/{slug(post.get('id') or post.get('slug') or bid)}"
        if post_id not in posts:
            ident = [{"@type": "PropertyValue", "propertyID": "local:democracyclub",
                      "value": str(post.get("id") or post.get("slug") or bid)}]
            posts[post_id] = {
                "@id": post_id, "@type": "Post",
                "roleName": post.get("label") or "Elected member",
                "memberOf": {"@id": admin_id, "name": admin["name"]},
                "roleClassification": "elected",
                "identifier": ident,
            }

        raw_sys = b.get("voting_system")
        system = SYSTEMS.get(raw_sys)
        if not system:
            gaps[f"votingSystem:{raw_sys}"] += 1
            system = "fptp"

        c = {
            "@id": f"{base}/contest/{slug(bid)}", "@type": "Contest",
            "name": f"{post.get('label') or bid} — {el.get('name') or eid}",
            "election": {"@id": elections[eid]["@id"], "name": elections[eid]["name"]},
            "contestType": "office",
            "electoralSystem": system,
            "post": {"@id": post_id, "name": posts[post_id]["roleName"]},
            "identifier": [{"@type": "PropertyValue", "propertyID": "local:democracyclub",
                            "value": bid}],
        }
        if b.get("winner_count"):
            c["seatsToFill"] = b["winner_count"]

        res = b.get("results") or {}
        counted = []
        for cand in b.get("candidacies") or []:
            person = cand.get("person") or {}
            pid = f"{base}/person/{person.get('id') or slug(person.get('name'))}"
            people[pid] = {"@id": pid, "@type": "Person",
                           "name": person.get("name") or "Unknown"}
            cy = {"@type": "Candidacy",
                  "candidate": {"@id": pid, "name": people[pid]["name"]}}
            pn = cand.get("party_name")
            if pn:
                party = cand.get("party") or {}
                ec = party.get("ec_id")
                party_id = f"{base}/party/{slug(ec or pn)}"
                parties[party_id] = {
                    "@id": party_id, "@type": "PoliticalParty", "name": pn,
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "local:electoral-commission",
                                    "value": str(ec or slug(pn))}]}
                cy["party"] = {"@id": party_id, "name": pn}
            r = cand.get("result") or {}
            if r.get("num_ballots") is not None:
                cy["voteCount"] = r["num_ballots"]
                counted.append(r["num_ballots"])
            if cand.get("elected") is not None:
                cy["candidacyResult"] = "elected" if cand["elected"] else "notElected"
            if cand.get("party_list_position"):
                cy["ballotOrder"] = cand["party_list_position"]
            c.setdefault("candidacy", []).append(cy)

        if res.get("num_spoilt_ballots") is not None:
            c["invalidVotes"] = res["num_spoilt_ballots"]
        if counted:
            c["validVotes"] = sum(counted)
            if c.get("invalidVotes") is not None:
                c["totalVotes"] = c["validVotes"] + c["invalidVotes"]
                turnout = res.get("num_turnout_reported")
                if turnout and turnout != c["totalVotes"]:
                    notes["reported turnout differs from valid plus spoilt ballots"] += 1

        # The profile stores the register rather than a derived percentage, so that
        # turnout can be recomputed against a corrected electorate. Democracy Club
        # publishes total_electorate, so the percentage is not carried at all.
        if res.get("total_electorate"):
            c["registeredVoters"] = res["total_electorate"]
        elif res.get("turnout_percentage") is not None:
            notes["turnout percentage published without an electorate; not carried, "
                  "since a derived figure cannot be recomputed"] += 1

        elections[eid]["contest"].append({"@id": c["@id"], "name": c["name"]})
        contests.append(c)

    # ballots cast, aggregated per election from its contests
    for eid, e in elections.items():
        ids = {r["@id"] for r in e["contest"]}
        cast = sum(c.get("totalVotes", 0) for c in contests if c["@id"] in ids)
        if cast:
            e["ballotsCast"] = cast

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    for fname, graph in (("jurisdictions.jsonld", [jurisdiction]),
                         ("organizations.jsonld", [admin]),
                         ("posts.jsonld", list(posts.values())),
                         ("people.jsonld", list(people.values())),
                         ("elections.jsonld", list(elections.values()) + contests
                          + list(parties.values()))):
        (out / fname).write_text(
            json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")

    print(f"democracyclub adapter: {args.date} -> {len(elections)} election(s), "
          f"{len(contests)} contest(s), {len(parties)} part(ies), {len(people)} candidate(s)")
    print(f"  written to {out}/")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1])[:8]:
                print(f"    {k}  ({n}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
