"""Does a pre-fit diagnostic predict whether the method will help?

The real datasets cannot answer this: under the final protocol the method ties the
tuned pooled model on every one of them, so the outcome has no variance to predict.
The synthetic factorial does have variance -- it was constructed to -- so the
diagnostics are validated there, on the configurations whose outcomes are already
measured in ``results/synthetic_suite_1se.csv``.

For each configuration the generator is re-instantiated with the same seed, the
diagnostics are computed from the data alone (no outcome of the fit is used), and
they are regressed on the measured difference against the tuned indicator model.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_real_suite import diagnostics  # noqa: E402
from synthgen import make_dataset  # noqa: E402

NPAT = {0.9: 12, 0.5: 60, 0.1: 300}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="results/synthetic_suite_1se.csv")
    ap.add_argument("--out", default="results/diagnostic_validation.csv")
    a = ap.parse_args()
    suite = pd.read_csv(a.suite)
    rows = []
    for i, r in suite.iterrows():
        X, y, _ = make_dataset(n=int(r["n"]), d=16, n_patterns=NPAT[r["concentration"]],
                               concentration=r["concentration"], mechanism=r["mechanism"],
                               het=r["het"], info=r["info"], prevalence=0.10,
                               target_miss=0.12, seed=0)
        dg = diagnostics(X, y)
        rows.append({**{k: r[k] for k in ["mechanism", "het", "info", "concentration", "n"]},
                     **dg, "delta": r["delta_vs_tuned_ind"], "p": r["p_vs_tuned_ind"]})
        if (i + 1) % 12 == 0:
            print(f"  {i+1}/{len(suite)} configurations", flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.to_csv(a.out, index=False)

    print(f"\nwrote {a.out} ({len(out)} configurations)\n")
    print("Spearman correlation with the measured delta:")
    for c in ["het_excess", "het", "cov30", "iota", "eff_pat", "miss", "n"]:
        v = out[c].to_numpy(float); ok = np.isfinite(v)
        r = stats.spearmanr(v[ok], out["delta"].to_numpy()[ok])
        print(f"  {c:12s} rho={r.statistic:+.3f}  p={r.pvalue:.2e}")

    # a diagnostic is only useful if it separates the cells where the method won
    out["won"] = (out["p"] < 0.05) & (out["delta"] > 0)
    print(f"\nSeparation of the {int(out.won.sum())} winning configurations "
          f"from the {int((~out.won).sum())} others:")
    for c in ["het_excess", "het", "cov30", "iota"]:
        w, l = out.loc[out.won, c], out.loc[~out.won, c]
        try:
            auc = stats.mannwhitneyu(w.dropna(), l.dropna()).statistic / (len(w.dropna()) * len(l.dropna()))
        except Exception:
            auc = float("nan")
        print(f"  {c:12s} won mean={w.mean():+.3f}  other mean={l.mean():+.3f}  AUC={auc:.3f}")

    # the synthetic study says two conditions must hold together
    out["combo"] = out["het_excess"] * out["cov30"]
    v = out["combo"].to_numpy(float); ok = np.isfinite(v)
    r = stats.spearmanr(v[ok], out["delta"].to_numpy()[ok])
    w, l = out.loc[out.won, "combo"], out.loc[~out.won, "combo"]
    auc = stats.mannwhitneyu(w.dropna(), l.dropna()).statistic / (len(w.dropna()) * len(l.dropna()))
    print(f"\n  het_excess x cov30   rho={r.statistic:+.3f} p={r.pvalue:.2e}  AUC={auc:.3f}")


if __name__ == "__main__":
    main()
