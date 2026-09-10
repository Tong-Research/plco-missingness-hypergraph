"""Step 0: is the pattern hierarchy usable on real PLCO data?

The hierarchical-shrinkage estimator fits one submodel per REALISED
missingness pattern and shrinks it toward its realised ancestors. If
patterns are near-unique there is no support to fit a submodel and the
estimator silently degenerates to a global model whatever the shrinkage
strength kappa is. This script measures whether the pattern structure can
support the method at all, BEFORE the expensive main experiment runs.

Reports every PLCO cohort under BOTH feature sets --
    "baseline" (default, the PRIMARY analysis: variables measured at or
                before randomisation)
    "full"     (sensitivity analysis: everything that survives the leakage
                exclusions, including later screening rounds / follow-up
                waves)
-- and at BOTH subsample levels --
    "full"    the entire loaded cohort
    "n40000"  the stratified, seeded n<=40,000 subsample the main experiment
              actually trains on (a memory-heavy baseline needs the cap to
              run at full model strength). Since the experiment only ever
              sees the subsampled pattern structure, that is the one that
              determines whether the method has support to work with -- the
              full-n numbers are reported for context, not as the gate.

Verdict thresholds (Task 14 brief):
    USABLE   -- median support-to-size ratio >= 10 AND n_patterns <= 5% of n
    MARGINAL -- median support-to-size ratio >= 3 (and not USABLE)
    HOPELESS -- otherwise: shrinkage returns the global model whatever
                kappa is

Caveat on iota (mask informativeness): it is unbiased but noisy at small
effective sample size -- measured sd is about 0.09 at n=600 with 5%
positives, falling to about 0.04 at n=2,000. These cohorts are far larger
(thousands of positives even after the n=40,000 cap), so the point estimate
is stable, but it remains a single cross-validated estimate, not an exact
quantity -- treat small iota differences between cohorts with that in mind.

NOTE on the brief's "44 to 61 patterns" figure: that was a placeholder
written before the data was profiled and is wrong by roughly two orders of
magnitude. Real prostate baseline data realises on the order of 2,900-5,400
patterns depending on subsample. This script reports what it measures, not
the placeholder.
"""

from __future__ import annotations

import os

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit

from hgmiss.data.plco import COHORTS, FEATURE_SETS, load_cohort
from hgmiss.maskinfo import mask_informativeness
from hgmiss.patterns import extract_patterns, immediate_ancestors, supports_for

ROOT = Path(os.environ.get("PLCO_ROOT",
                           "/Users/tong/Works/tong/phd/datasets/plco"))
OUT = Path("results")
OUT.mkdir(exist_ok=True)

SUBSAMPLE_N = 40_000
SEED = 0  # both the stratified subsample draw and mask_informativeness's CV


def stratified_subsample(
    X: np.ndarray, y: np.ndarray, mask: np.ndarray, n: int, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
    """Stratified (by outcome), seeded subsample to at most ``n`` rows.

    Returns the data unchanged (and ``applied=False``) if the cohort is
    already at or below the cap -- matches what the main experiment does.
    """
    n_rows = X.shape[0]
    if n_rows <= n:
        return X, y, mask, False
    splitter = StratifiedShuffleSplit(n_splits=1, train_size=n, random_state=seed)
    idx, _ = next(splitter.split(X, y))
    return X[idx], y[idx], mask[idx], True


def gate_row(cohort: str, feature_set: str, subsample: str, X, y, mask) -> dict:
    n, d = X.shape
    counts = extract_patterns(mask)
    # Drop the empty pattern (a row with everything missing): support/|e| is
    # undefined at |e|=0, and it carries no ancestor structure to shrink with.
    pats = [e for e in counts if e]
    sup = supports_for(pats, mask)
    ratios = [sup[e] / len(e) for e in pats]
    anc = immediate_ancestors(pats)
    with_anc = sum(1 for e in pats if anc[e])
    iota = mask_informativeness(mask, y, seed=SEED)

    n_patterns = len(pats)
    median_ratio = float(np.median(ratios)) if ratios else 0.0
    if median_ratio >= 10 and n_patterns <= 0.05 * n:
        verdict = "USABLE"
    elif median_ratio >= 3:
        verdict = "MARGINAL"
    else:
        verdict = "HOPELESS"

    return {
        "cohort": cohort,
        "feature_set": feature_set,
        "subsample": subsample,
        "n": n,
        "d": d,
        "prevalence": float(y.mean()),
        "missing_rate": float((~mask).mean()),
        "n_patterns": n_patterns,
        "median_support_ratio": median_ratio,
        "frac_with_ancestor": with_anc / max(n_patterns, 1),
        "iota": iota,
        "verdict": verdict,
    }


def main() -> None:
    rows = []
    for cohort in sorted(COHORTS):
        for feature_set in FEATURE_SETS:
            print(f"loading {cohort} / {feature_set} ...", flush=True)
            c = load_cohort(cohort, ROOT, feature_set=feature_set)

            row_full = gate_row(cohort, feature_set, "full", c.X, c.y, c.mask)
            rows.append(row_full)
            print(f"  full:   {row_full}", flush=True)

            Xs, ys, ms, applied = stratified_subsample(
                c.X, c.y, c.mask, SUBSAMPLE_N, SEED
            )
            if not applied:
                print(
                    f"  note: {cohort}/{feature_set} has n={c.X.shape[0]} "
                    f"<= cap ({SUBSAMPLE_N}); n40000 row equals full",
                    flush=True,
                )
            row_sub = gate_row(cohort, feature_set, "n40000", Xs, ys, ms)
            rows.append(row_sub)
            print(f"  n40000: {row_sub}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "gate.csv", index=False)

    print("\nVERDICT TABLE")
    header = (
        f"{'cohort':12s} {'feature_set':11s} {'subsample':9s} {'n':>8s} "
        f"{'d':>4s} {'patterns':>9s} {'ratio':>7s} {'frac_anc':>9s} "
        f"{'iota':>7s}  verdict"
    )
    print(header)
    print("-" * len(header))
    for r in df.itertuples():
        print(
            f"{r.cohort:12s} {r.feature_set:11s} {r.subsample:9s} {r.n:8,d} "
            f"{r.d:4d} {r.n_patterns:9,d} {r.median_support_ratio:7.1f} "
            f"{r.frac_with_ancestor:9.3f} {r.iota:7.3f}  {r.verdict}"
        )

    print(
        "\nNote: iota is a single cross-validated AUROC-0.5 estimate; "
        "measured sd is ~0.09 at n=600/5% positive, ~0.04 at n=2000 -- "
        "stable at these cohort sizes but not exact."
    )


if __name__ == "__main__":
    main()
