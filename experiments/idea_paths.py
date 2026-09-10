"""Where an idea may write, and the reason the boundary is exactly here.

Three globs decide what reaches the papers:

    fingerprint.py      results/main.csv, results/main_*.csv, results/rebuild-*/main.csv
    ingest_results.py   the same three
    decision_census.py  results/*.csv, filtered to files whose columns include `target`
                        together with `n_partners` or `helped`

Anything matching the first two enters Paper 1's tables and its committed checksums. Anything
matching the third is counted as a merge decision in Paper C's headline 986,254.

`results/ideas/<ID>/` matches none of them: not `main_*.csv` at the top level, not `rebuild-*/`,
and one directory down from the census glob. That is why ideas live there and not in a file called
`main_IDEA.csv`, which would be picked up by fingerprint.py on its next run and silently enter the
paper's table as a thirteenth method.

`open_for_write` refuses any path outside that tree. The 2026-08-24 loss of 1,850 rows happened
because a job declared a shared file as its output; the cheapest defence is to make the wrong path
impossible rather than discouraged.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDEAS = ROOT / "results" / "ideas"
# a trailing lowercase letter marks a revision of an earlier idea (A4 -> A4b), kept as a
# separate id so the superseded run stays reproducible in its own directory
ID_RE = re.compile(r"^[A-Z]\d{1,2}[a-z]?(_[a-z0-9_]+)?$")

# Cohorts held out for testing. Ideas are developed on the other two; anything tuned on all four
# cannot be reported as validated on any of them.
DEV = ("colorectal", "lung")
HOLDOUT = ("ovarian", "prostate")


def idea_dir(idea: str) -> pathlib.Path:
    if not ID_RE.match(idea):
        raise ValueError(f"idea id {idea!r} must look like A4, A4b or B7_adaptive")
    d = IDEAS / idea
    d.mkdir(parents=True, exist_ok=True)
    return d


def open_for_write(idea: str, name: str):
    """The only sanctioned way for an idea to write. Refuses anything outside its own directory."""
    d = idea_dir(idea)
    p = (d / name).resolve()
    if not str(p).startswith(str(d.resolve()) + "/"):
        raise ValueError(f"refusing to write outside {d}: {p}")
    return p.open("w", newline="")


def check_cohort(cohort: str, unblind: bool = False) -> None:
    """Refuse a holdout cohort unless the caller says so explicitly."""
    if cohort in HOLDOUT and not unblind:
        raise SystemExit(
            f"{cohort} is held out for testing (holdout: {', '.join(HOLDOUT)}).\n"
            f"Develop on {', '.join(DEV)}. Pass --unblind only when the idea is finished and you\n"
            f"are reporting its test result, and record that you did so -- an idea tuned on the\n"
            f"holdout has no holdout."
        )


def method_name(idea: str, label: str) -> str:
    """Idea methods carry a prefix so a leak into the main table is loud rather than quiet:
    figures/ingest_results.py raises on any method absent from METHOD_MAP."""
    return f"idea_{idea}_{label}"
