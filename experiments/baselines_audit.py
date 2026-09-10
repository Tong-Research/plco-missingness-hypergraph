"""Does the Baselines section describe the experiment that was actually run?

FINISHING.md carried this as BLOCKING for weeks: the section claimed 28 imputer-by-classifier
combinations, XGBoost, LightGBM and four pattern-based methods, while `main.csv` held seven
methods. It was resolved by rewriting the section and by the missing baselines finishing -- but
nothing stopped it drifting apart again, and drift in this direction is the most damaging kind a
paper can have. A reader can check every number in a table and never notice that the table is
missing a method the prose promised.

So the correspondence is asserted, both ways:

  * every method named in the section exists in the results, and
  * every method in the results is named in the section,

plus the count word in the prose. The grouping below is the section's own, kept here rather than
parsed out of the LaTeX, because parsing prose for method names is how a check starts passing for
the wrong reason.

Usage: baselines_audit.py
"""
from __future__ import annotations

import pathlib
import re
import sys

import pandas as pd

R = pathlib.Path(__file__).resolve().parent.parent / "results"
TEX = pathlib.Path(__file__).resolve().parent.parent / "sections-experiment.tex"

# The section's four groups plus the proposed method. Update BOTH this and the prose together.
GROUPS = {
    "imputation then logistic regression": ["mean_impute", "mice_impute_lr"],
    "mask-augmented":                      ["mean_indicator", "mask_interaction"],
    "native missing-value classifiers":    ["histgb_native", "xgboost_native", "lightgbm_native"],
    "pattern-based":                       ["pattern_submodels", "spsm_global", "learnpp_mf",
                                            "refe", "refe_tree"],
    "the proposed method":                 ["ours"],
}
WORDS = {7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve",
         13: "Thirteen", 14: "Fourteen"}
FULL_N = 40_000


def main() -> int:
    srcs = [R / "main.csv", *sorted(R.glob("main_*.csv")), *sorted(R.glob("rebuild-*/main.csv"))]
    frames = []
    for s in srcs:
        if not s.exists():
            continue
        try:
            d = pd.read_csv(s)
        except Exception:                                        # noqa: BLE001
            continue
        if {"cohort", "method", "auprc", "seed", "fold"} <= set(d.columns):
            frames.append(d)
    if not frames:
        print("  no result files"); return 1
    df = pd.concat(frames, ignore_index=True)
    df = df[(df.subsample_n == FULL_N) & (df.feature_set == "baseline")]
    have = set(df.method.unique())
    claimed = [m for v in GROUPS.values() for m in v]

    problems = []
    print(f"  results carry {len(have)} methods; the section describes {len(claimed)}")
    for g, ms in GROUPS.items():
        miss = [m for m in ms if m not in have]
        print(f"    {g:38s} {len(ms)}  {'ok' if not miss else 'MISSING FROM RESULTS: ' + str(miss)}")
        problems += [f"section promises {m!r}, results have no such method" for m in miss]
    for m in sorted(have - set(claimed)):
        problems.append(f"results contain {m!r}, the section never mentions it")

    tex = TEX.read_text()
    # Any stated count of methods, not one exact sentence. The section says "all
    # thirteen methods" and the audit demanded "N methods are compared", so a
    # correct section reported as a problem while the count itself went
    # unchecked. Every stated count must agree with the results.
    want = WORDS.get(len(have), str(len(have)))
    lowered = {v.lower() for v in WORDS.values()}
    stated = [w for w in re.findall(r"(\w+)\s+methods\b", tex)
              if w.lower() in lowered or w.isdigit()]
    if not stated:
        problems.append(f"the section states no method count at all; the results hold "
                        f"{len(have)} ({want!r}). NOT ANCHORED, not a pass.")
    else:
        bad = sorted({w for w in stated if w.lower() != want.lower()})
        if bad:
            problems.append(f"the section says {bad} methods; the results hold "
                            f"{len(have)}, which is {want!r}")
        else:
            print(f"    count word {want!r} matches the {len(have)} methods present "
                  f"({len(stated)} mention(s))")

    # every named method must also be complete, or the prose promises a comparison it cannot make
    n_cells = df.groupby("method").size()
    for m in claimed:
        if m in have and n_cells.get(m, 0) != 50 * df.cohort.nunique():
            problems.append(f"{m!r} has {n_cells.get(m, 0)} cells, not "
                            f"{50 * df.cohort.nunique()} -- incomplete but described as compared")

    # ---- the PROPOSED method, not only the comparators (Result 159). The method section once
    # described tau-thresholded pairwise regressions combined by |rho|-weight, and the code fits
    # one multivariate logistic regression per pattern; tau never existed in src/. Nothing here
    # can prove the prose matches _fit_one, but it can refuse the specific words that were wrong,
    # and require the one that is right.
    mtex = (TEX.parent / "sections-method.tex").read_text()
    banned = {r"\tau": "a correlation threshold the code does not have",
              r"\rho^{e}": "per-pattern pairwise correlations the code does not compute",
              "pairwise regression": "a pairwise local model; the code fits one joint regression",
              "pairwise statistics": "per-pattern pair statistics the code does not compute",
              "edge regression": "the old per-edge model; the code fits one joint regression",
              "quadratic": "a quadratic edge form that was never implemented",
              "FitRegression": "the old pairwise fit; the code calls one logistic fit"}
    for tok, why in banned.items():
        if tok in mtex:
            problems.append(f"method section still contains {tok!r}: {why}")
    if "LogisticFit" not in mtex and "logistic regression" not in mtex.lower():
        problems.append("method section never says the per-pattern model is a logistic regression")
    print(f"  method section: {len([t for t in banned if t in mtex])} banned token(s), "
          f"logistic {'named' if 'logistic' in mtex.lower() else 'NOT named'}")

    print()
    if problems:
        print("  PROBLEMS:")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  the Baselines section describes exactly the experiment that was run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
