#!/usr/bin/env python3
"""Prove the validators reject what they should.

examples/_invalid holds one deliberately wrong node per fault. Passing data proves
nothing if a validator is silently accepting everything, so this asserts that every
faulty node is flagged by at least one tier, and that the clean nodes are not.

Usage:  python3 tools/check-invalid.py
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://invalid.example/id/"

# fault node -> what is wrong with it
FAULTS = {
    "project/bad-status": "status outside the code list",
    "project/bad-date": "malformed date",
    "project/bad-phase-shape": "phase given as free text",
    "project/ms-missing": "milestone missing name and about",
    "project/backwards": "ends before it starts",
    "project/ms-scheduled-met": "scheduled milestone carries dateMet",
    "project/dangling": "reference to an entity that does not exist",
    "project/phase-is-org": "phase points at an organization",
    "project/phase-no-scheme": "phase belongs to no lifecycle scheme",
    "project/phase-wrong-scheme": "phase claims a scheme that does not list it",
    "project/owner-is-place": "responsible organization is a place",
    "project/ms-about-org": "milestone is about an organization",
    "budget-line/line-part-of-org": "budget line whose parent is not a budget line",
    "organization/unit-bad-mission": "mission is not text",
    "budget-line/line-fund-is-org": "budget line whose fund is an organization",
    "fund/no-name": "fund with no name",
    "fund/administered-by-place": "fund administered by a jurisdiction",
    "budget-line/line-program-is-fund": "budget line whose program is a fund",
    "program/no-name": "program with no name",
    "program/administered-by-place": "program administered by a jurisdiction",
    "organization/unit-bad-class": "classification outside the code list",
    "organization/unit-parent-is-place": "parentOrganization points at a jurisdiction",
    "organization/unit-cycle-a": "parentOrganization cycle",
    "organization/unit-lists-wrong-parent": "lists a child that names a different parent",
    "organization/unit-government-with-parent": "a government (root) that has a parent",
    "policy/no-label": "provision with neither a name nor an identifier",
    "policy/no-jurisdiction": "top-level work with no jurisdiction",
    "policy/part-of-org": "isPartOf points at an organization",
    "policy/cycle-a": "isPartOf cycle",
    "policy/lists-wrong-parent": "lists a child that names a different parent",
    "policy/bad-type": "legislationType outside the code list",
    "policy/dangling-citation": "citation points at an entity that does not exist",
    "policy/bad-date": "malformed effective date",
    "policy/bad-date-month": "effective date with a month outside 01-12",
    "policy/bad-date-short-year": "effective date as an ambiguous two-digit-year string",
    "policy/passed-by-place": "approving body is a jurisdiction",
    "policy/citation-is-org": "citation points at an organization",
    "policy/term-bad-set": "definition belongs to something that is not a term set",
    "policy/term-subject-org": "definition's source is an organization",
    "policy/term-no-name": "definition with no name",
    "statistics/no-variable": "observation with no measured variable",
    "statistics/no-value": "observation with no value",
    "statistics/no-dataset": "observation with no source dataset",
    "statistics/both-time": "both observationDate and observationPeriod",
    "statistics/no-time": "neither observationDate nor observationPeriod",
    "statistics/bad-period": "period not an ISO 8601 interval",
    "statistics/backwards-period": "period ends before it starts",
    "statistics/bad-moe": "negative margin of error",
    "statistics/bad-confidence": "confidence level outside 0 to 1",
    "statistics/bad-bounds": "lower bound above upper bound",
    "statistics/dataset-is-org": "sourceDataset points at an organization",
    "statistics/variable-is-place": "variableMeasured points at a place",
    "statistics/var-no-name": "variable with no name",
    "statistics/area-no-type": "statistical area with no areaType",
    "statistics/area-bad-type": "areaType outside the code list",
    "statistics/area-governed": "statistical area with a governing organization",
    "statistics/area-in-org": "statistical area contained in an organization",
}
CLEAN = ["project/ok", "organization/o", "organization/unit-ok", "organization/unit-child-ok",
         "policy/clean-top", "policy/clean-part", "policy/term-ok", "policy/partial-date-ok",
         "statistics/ok", "statistics/ok-period", "statistics/ok-no-uncertainty", "statistics/area-ok",
         "statistics/var-ok"]


def run(tool):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "examples/_invalid"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    rc_v, out_v = run("validate.py")
    rc_s, out_s = run("shacl.py")
    problems = []
    if rc_v == 0:
        problems.append("validate.py accepted the invalid fixture")
    if rc_s == 0:
        problems.append("shacl.py accepted the invalid fixture")

    caught_v = {k for k in FAULTS if BASE + k in out_v}
    caught_s = {k for k in FAULTS if BASE + k in out_s}
    for k, why in FAULTS.items():
        if k not in caught_v | caught_s:
            problems.append(f"not flagged by either tier: {k} ({why})")
    for k in CLEAN:
        if BASE + k in out_v.split("error(s)")[-1] or BASE + k in out_s.split("violation(s)")[-1]:
            problems.append(f"clean node was flagged: {k}")

    print(f"check-invalid: {len(FAULTS)} faults; "
          f"validate.py flagged {len(caught_v)}, shacl.py flagged {len(caught_s)}, "
          f"{len(caught_s - caught_v)} only by SHACL, {len(caught_v - caught_s)} only by validate.py")
    if problems:
        print("\nFAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK - every fault is rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
