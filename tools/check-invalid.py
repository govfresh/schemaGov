#!/usr/bin/env python3
"""Prove the validators reject what they should.

examples/_invalid holds one deliberately wrong node per fault. Passing data proves
nothing if a validator is silently accepting everything, so this asserts that every
faulty node is flagged by at least one tier, and that the clean nodes are not.

Each fault names the message that must reject it. A node rejected for some other
reason, such as a missing field the fixture forgot, does not count: that would hide a
check that no longer runs.

Usage:  python3 tools/check-invalid.py
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://invalid.example/id/"

# fault node -> (what is wrong with it, part of the message that must reject it)
FAULTS = {
    "project/cost-no-currency": ("estimated cost with no currency",
        "estimatedCost: 'currency' is a required property"),
    "project/category-not-list": ("project category that is not a list",
        "projectCategory: 'Drainage' is not of type 'array'"),
    "format/url-with-space": ("IRI containing a space",
        "is not a 'iri'"),
    "format/url-relative": ("relative IRI",
        "is not a 'iri'"),
    "format/url-no-host": ("web IRI with no host",
        "is not a 'iri'"),
    "format/time-no-zone": ("date-time with no time zone",
        "dateModified: '2026-01-02T03:04:05' is not valid"),
    "format/time-impossible": ("date-time that does not exist",
        "dateModified: '2026-02-30T03:04:05Z' is not valid"),
    "project/bad-status": ("status outside the code list",
        "status: 'blocked' is not one of"),
    "project/bad-date": ("malformed date",
        "startDate: '15/01/2026' is not a 'date'"),
    "project/bad-phase-shape": ("phase given as free text",
        "phase: 'beta' is not of type 'object'"),
    "project/ms-missing": ("milestone missing name and about",
        "'about' is a required property"),
    "project/backwards": ("ends before it starts",
        "project ended before it started"),
    "project/ms-scheduled-met": ("scheduled milestone carries dateMet",
        "milestone has dateMet but is scheduled"),
    "project/dangling": ("reference to an entity that does not exist",
        "dangling reference"),
    "project/phase-is-org": ("phase points at an organization",
        "A project has at most one phase, and it must be a DefinedTerm"),
    "project/phase-no-scheme": ("phase belongs to no lifecycle scheme",
        "phase must belong to a lifecycle scheme"),
    "project/phase-wrong-scheme": ("phase claims a scheme that does not list it",
        "claims a lifecycle scheme that is not the one that lists the term"),
    "project/owner-is-place": ("responsible organization is a place",
        "The responsible organization must be an organization"),
    "project/ms-about-org": ("milestone is about an organization",
        "A milestone must be about exactly one Project"),
    "budget-line/line-part-of-org": ("budget line whose parent is not a budget line",
        "A budget line's parent must be another budget line"),
    "organization/unit-bad-mission": ("mission is not text",
        "mission: 42 is not of type 'string'"),
    "budget-line/line-fund-is-org": ("budget line whose fund is an organization",
        "fund must point at a Fund"),
    "fund/no-name": ("fund with no name",
        "'name' is a required property"),
    "fund/administered-by-place": ("fund administered by a jurisdiction",
        "A fund's administeredBy must be a government organization"),
    "budget-line/line-program-is-fund": ("budget line whose program is a fund",
        "program must point at a Program"),
    "budget-line/line-project-is-org": ("budget line whose project is an organization",
        "project must point at a Project"),
    "jurisdiction/within-org": ("jurisdiction within an organization",
        "geoWithin must point at a place or jurisdiction"),
    "jurisdiction/overlaps-org": ("jurisdiction overlapping an organization",
        "geoOverlaps must point at a place or jurisdiction"),
    "ngo/no-name": ("non-government organization with no name",
        "'name' is a required property"),
    "ngo/classified": ("non-government organization with a government classification",
        "False schema does not allow 'authority'"),
    "ngo/parent-is-government": ("non-government organization under a government body",
        "An NGO's parentOrganization must be another non-government organization"),
    "program/no-name": ("program with no name",
        "'name' is a required property"),
    "program/administered-by-place": ("program administered by a jurisdiction",
        "A program's administeredBy must be a government organization"),
    "organization/unit-bad-class": ("classification outside the code list",
        "organizationClassification: 'random-department-kind' is not one of"),
    "organization/unit-parent-is-place": ("parentOrganization points at a jurisdiction",
        "parentOrganization is not an organization"),
    "organization/unit-cycle-a": ("parentOrganization cycle",
        "parentOrganization cycle"),
    "organization/unit-lists-wrong-parent": ("lists a child that names a different parent",
        "hierarchy disagrees"),
    "organization/unit-government-with-parent": ("a government (root) that has a parent",
        "is the root of its tree and has no parent"),
    "organization/unit-bad-scheme": ("identifier scheme that is neither registered nor prefixed",
        "propertyID: 'erp-org-unit' is not valid"),
    "role/no-member": ("role that names no person",
        "'member' is a required property"),
    "policy/file-no-content-url": ("legislation file with no contentUrl",
        "'contentUrl' is a required property"),
    "policy/no-label": ("provision with neither a name nor an identifier",
        "is not valid under any of the given schemas"),
    "policy/no-jurisdiction": ("top-level work with no jurisdiction",
        "'legislationJurisdiction' is a required property"),
    "policy/part-of-org": ("isPartOf points at an organization",
        "isPartOf is not legislation"),
    "policy/cycle-a": ("isPartOf cycle",
        "Legislation must not be part of itself"),
    "policy/lists-wrong-parent": ("lists a child that names a different parent",
        "hierarchy disagrees"),
    "policy/bad-type": ("legislationType outside the code list",
        "legislationType: 'personnelRegulation' is not one of"),
    "policy/dangling-citation": ("citation points at an entity that does not exist",
        "citation must be the citation as written"),
    "policy/bad-date": ("malformed effective date",
        "legislationDateOfApplicability: 'April 1' does not match"),
    "policy/bad-date-month": ("effective date with a month outside 01-12",
        "legislationDateOfApplicability: '2005-13' does not match"),
    "policy/bad-date-short-year": ("effective date as an ambiguous two-digit-year string",
        "legislationDateOfApplicability: '02-07-17' does not match"),
    "policy/passed-by-place": ("approving body is a jurisdiction",
        "legislationPassedBy must point at the body that adopted it"),
    "policy/citation-is-org": ("citation points at an organization",
        "citation must be the citation as written"),
    "policy/term-bad-set": ("definition belongs to something that is not a term set",
        "inDefinedTermSet must point at a DefinedTermSet"),
    "policy/term-subject-org": ("definition's source is an organization",
        "subjectOf must point at the piece of Legislation"),
    "policy/term-no-name": ("definition with no name",
        "'name' is a required property"),
    "statistics/no-variable": ("observation with no measured variable",
        "'variableMeasured' is a required property"),
    "statistics/no-value": ("observation with neither a value nor a bound",
        "An observation needs a value, or a one-sided bound"),
    "statistics/moe-no-value": ("margin of error on a bound-only observation",
        "An observation with no value cannot have a marginOfError"),
    "statistics/only-moe": ("margin of error with no value and no bound",
        "An observation needs a value, or a one-sided bound"),
    "statistics/no-dataset": ("observation with no source dataset",
        "'sourceDataset' is a required property"),
    "statistics/both-time": ("both observationDate and observationPeriod",
        "exactly one of observationDate and observationPeriod"),
    "statistics/no-time": ("neither observationDate nor observationPeriod",
        "exactly one of observationDate and observationPeriod"),
    "statistics/bad-period": ("period not an ISO 8601 interval",
        "observationPeriod: '2019-2023' does not match"),
    "statistics/backwards-period": ("period ends before it starts",
        "period must not end before it starts"),
    "statistics/bad-moe": ("negative margin of error",
        "is less than the minimum of 0"),
    "statistics/bad-confidence": ("confidence level outside 0 to 1",
        "is greater than the maximum of 1"),
    "statistics/bad-bounds": ("lower bound above upper bound",
        "The lower bound must not exceed the upper bound"),
    "statistics/dataset-is-org": ("sourceDataset points at an organization",
        "sourceDataset must point at a Dataset"),
    "statistics/variable-is-place": ("variableMeasured points at a place",
        "An observation must name the StatisticalVariable it measures"),
    "statistics/var-no-name": ("variable with no name",
        "'name' is a required property"),
    "statistics/area-no-type": ("Place with no areaType that carries a statistical-area property",
        "a Place without areaType is read as a facility"),
    "statistics/area-bad-type": ("areaType outside the code list",
        "areaType: 'county' is not one of"),
    "statistics/area-governed": ("statistical area with a governing organization",
        "A statistical area has no governing authority"),
    "statistics/area-in-org": ("statistical area contained in an organization",
        "A statistical area lies within a jurisdiction or another area"),
}
CLEAN = ["project/ok", "format/ok", "ngo/ok", "project/cost-ok", "budget-line/line-ok", "jurisdiction/within-ok", "organization/unit-census-geoid-ok", "organization/o", "organization/unit-ok", "organization/unit-child-ok",
         "policy/clean-top", "policy/clean-part", "policy/term-ok", "policy/partial-date-ok",
         "statistics/ok", "statistics/ok-period", "statistics/ok-no-uncertainty", "statistics/area-ok",
         "statistics/var-ok", "statistics/facility-place-ok", "statistics/bound-only-ok",
         "statistics/bound-max-only-ok"]


def run(tool):
    """The tool's exit code and its errors, one string per error. Warnings are left out."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "examples/_invalid"],
                       cwd=ROOT, capture_output=True, text=True)
    errors, inside = [], False
    for line in r.stdout.splitlines():
        if re.match(r"\d+ (error|violation|warning)\(s\):", line):
            inside = "warning" not in line
        elif inside and line.startswith("  - "):
            errors.append(line[4:])
        elif inside and line.startswith("    "):
            errors[-1] += "\n" + line
    return r.returncode, errors


def about(node, errors):
    """The errors that mention this node, matched on its whole @id."""
    pattern = re.compile(re.escape(BASE + node) + r"(?![\w/-])")
    return [e for e in errors if pattern.search(e)]


def main():
    rc_v, err_v = run("validate.py")
    rc_s, err_s = run("shacl.py")
    problems = []
    if rc_v == 0:
        problems.append("validate.py accepted the invalid fixture")
    if rc_s == 0:
        problems.append("shacl.py accepted the invalid fixture")

    caught_v = {k for k in FAULTS if about(k, err_v)}
    caught_s = {k for k in FAULTS if about(k, err_s)}
    for k, (why, message) in FAULTS.items():
        got = about(k, err_v + err_s)
        if not any(message in e for e in got):
            problems.append(
                f"not rejected for its own fault: {k} ({why})\n"
                f"      expected a message containing: {message}\n"
                f"      got: {'; '.join(' '.join(e.split()) for e in got) or 'nothing'}")
    for k in CLEAN:
        if about(k, err_v + err_s):
            problems.append(f"clean node was flagged: {k}")

    print(f"check-invalid: {len(FAULTS)} faults; "
          f"validate.py flagged {len(caught_v)}, shacl.py flagged {len(caught_s)}, "
          f"{len(caught_s - caught_v)} only by SHACL, {len(caught_v - caught_s)} only by validate.py")
    if problems:
        print("\nFAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK - every fault is rejected for its own reason")
    return 0


if __name__ == "__main__":
    sys.exit(main())
