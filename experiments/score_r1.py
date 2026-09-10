"""Score R1 against prereg/R1.md -- written and committed BEFORE the results existed.

Six predictions, three withdrawal conditions, one null contrast, exactly as registered. The
script refuses to score a cohort whose file is missing or short, so a partial run cannot be read
as a result.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

R = pathlib.Path(__file__).resolve().parent.parent / "results" / "ideas" / "R1"
FLOOR, CV_NOISE, EXACT = 0.002, 0.001, 1e-4
EXPECTED_ROWS = 4 * 25 * 2          # arms x (5 seeds x 5 folds) x (real, permuted)


def paired(piv, a, b):
    p = piv[[a, b]].dropna()
    d = (p[a] - p[b]).to_numpy(float)
    pv = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    return float(np.median(d)), pv, float(np.abs(d).max()), len(d)


def load(cohort):
    f = R / f"{cohort}.csv"
    if not f.exists():
        raise SystemExit(f"  {cohort}: {f.name} MISSING -- refusing to score")
    d = pd.read_csv(f)
    if len(d) < EXPECTED_ROWS:
        raise SystemExit(f"  {cohort}: {len(d)} of {EXPECTED_ROWS} rows -- run incomplete, refusing")
    d["arm"] = d.arm.str.replace("idea_R1_", "", regex=False)
    return d


def main() -> int:
    verdicts, withdraw = {}, []
    cohorts = tuple(sys.argv[1:]) or ("colorectal", "lung")   # score one cohort while the other runs
    for coh in cohorts:
        d = load(coh)
        real = d[d.permuted == 0].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
        null = d[d.permuted == 1].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
        print(f"\n  {coh.upper()}   " + "  ".join(f"{k}={v:.5f}" for k, v in real.mean().sort_values(ascending=False).items()))

        # P1 instrument: the corner IS the baseline
        m, p, mx, n = paired(real, "rooted_kinf", "mean_impute")
        p1 = (m == 0.0) and (mx < EXACT)
        print(f"    P1 rooted_kinf==mean_impute  median {m:+.2e} max|cell| {mx:.2e}  {'HOLDS' if p1 else 'FAILS -> withdrawal (a)'}")
        if not p1:
            withdraw.append(f"(a) {coh}: root is not the baseline"); continue

        # P2 never below baseline beyond CV noise
        m2, p2v, _, _ = paired(real, "rooted_cv", "mean_impute")
        p2 = m2 >= -CV_NOISE
        print(f"    P2 rooted_cv-mean_impute      median {m2:+.6f} p={p2v:.3g}  {'HOLDS' if p2 else 'FAILS'}")
        if m2 < -FLOOR:
            withdraw.append(f"(b) {coh}: rooted_cv below baseline by {m2:+.4f} -- inner CV cannot reach the corner")

        # P3 beats the frozen estimator at its published operating point
        m3, p3v, _, _ = paired(real, "rooted_cv", "ours_asis")
        p3 = (m3 >= FLOOR) and (p3v < 0.05)
        print(f"    P3 rooted_cv-ours_asis        median {m3:+.6f} p={p3v:.3g}  {'HOLDS' if p3 else 'FAILS'}")

        # P4/P5 vs the floor, and vs the published null
        gain_real = (real.rooted_cv - real.mean_impute).dropna()
        gain_null = (null.rooted_cv - null.mean_impute).dropna()
        ex = (gain_real - gain_null).dropna().to_numpy(float)
        ex_med = float(np.median(ex)); ex_p = float(stats.wilcoxon(ex).pvalue) if np.any(ex != 0) else 1.0
        clears = (m2 >= FLOOR) and (p2v < 0.05)
        beats_null = (ex_med >= FLOOR) and (ex_p < 0.05)
        tag = "P4" if coh == "lung" else "P5"
        print(f"    {tag} vs floor: {'CLEARS' if clears else 'below'} ({m2:+.6f})   "
              f"vs null: gain real {gain_real.median():+.6f} null {gain_null.median():+.6f} "
              f"excess {ex_med:+.6f} p={ex_p:.3g}  {'BEATS NULL' if beats_null else 'does not beat null'}")
        verdicts[coh] = dict(clears=clears, beats_null=beats_null)

        # P6 which kappa inner CV chose
        kc = d[(d.permuted == 0) & (d.arm == "rooted_cv")].kappa_chosen.astype(float)
        frac_inf = float(np.isinf(kc).mean())
        want_inf = coh == "lung"
        p6 = (frac_inf > 0.5) if want_inf else (frac_inf < 0.5)
        print(f"    P6 kappa=inf chosen in {frac_inf:.0%} of cells  "
              f"(predicted {'majority' if want_inf else 'minority'})  {'HOLDS' if p6 else 'FAILS'}")

    if len(verdicts) == 2 and all(v["clears"] and v["beats_null"] for v in verdicts.values()):
        withdraw.append("(c) rooted_cv clears the floor AND beats its null on BOTH dev cohorts -- "
                        "contradicts the nulls; replicate on the holdout (--unblind, recorded) "
                        "before touching the discussion")
    print("\n  " + ("WITHDRAWAL CONDITIONS FIRED:\n    - " + "\n    - ".join(withdraw) if withdraw
                    else "no withdrawal condition fired"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
