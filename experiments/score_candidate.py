"""Score prereg/HIGGS.md or prereg/PORTO.md from results/cand/<npz>.csv. Refuses incomplete files."""
import pathlib, sys
import numpy as np, pandas as pd
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOOR = 0.002

def paired(piv, a, b):
    d = (piv[a] - piv[b]).dropna().to_numpy(); return float(np.median(d)), (float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0), len(d)

def main(npz, seeds=3, folds=5):
    f = ROOT / "results" / "cand" / f"{npz}.csv"
    if not f.exists(): raise SystemExit(f"  {f} MISSING -- refusing")
    d = pd.read_csv(f); real = d[d.permuted == 0].pivot_table(index=["seed", "fold"], columns="arm", values="auprc"); null = d[d.permuted == 1].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
    if len(real) < seeds * folds: raise SystemExit(f"  {len(real)} of {seeds*folds} cells -- incomplete, refusing")
    print(f"  {npz}: {len(real)} cells; means " + " ".join(f"{a} {real[a].mean():.4f}" for a in real.columns))
    v = {}
    m1, p1, _ = paired(real, "ours", "mean_impute"); v["P1"] = m1 >= FLOOR and p1 < .05; print(f"    P1 ours-impute      {m1:+.4f} p={p1:.2g}  {'HOLDS' if v['P1'] else 'FAILS'}")
    ex = ((real["ours"] - real["mean_impute"]) - (null["ours"] - null["mean_impute"])).dropna().to_numpy(); exm = float(np.median(ex)); exp_ = float(stats.wilcoxon(ex).pvalue) if np.any(ex != 0) else 1.0
    v["P2"] = exm >= FLOOR and exp_ < .05; print(f"    P2 real-null excess  {exm:+.4f} p={exp_:.2g}  {'HOLDS' if v['P2'] else 'FAILS'}")
    m3, p3, _ = paired(real, "ours", "mean_indicator"); bar = 0.005 if npz == "cand_higgs" else 0.0; v["P3"] = m3 >= bar; print(f"    P3 ours-indicator   {m3:+.4f} p={p3:.2g} (bar {bar})  {'HOLDS' if v['P3'] else 'FAILS'}")
    m4, p4, _ = paired(real, "ours", "mask_interaction"); print(f"    P4 ours-interaction {m4:+.4f} p={p4:.2g}  {'within +-0.005' if abs(m4) <= 0.005 else 'OUTSIDE'}")
    m5, p5, _ = paired(real, "ours", "pattern_submodels"); print(f"    P5 ours-submodels   {m5:+.4f} p={p5:.2g}  {'within +-0.002' if abs(m5) <= 0.002 else ('INVERSION -> bug hunt' if m5 <= -0.002 else 'ours ahead')}")
    mp, _, _ = paired(real, "ours", "ours_projected"); print(f"    projection delta    {mp:+.4f}")
    mt = min(paired(real, "histgb_native", a)[0] for a in ["mean_impute", "mean_indicator", "mask_interaction", "ours"]); print(f"    P6 tree - best linear {mt:+.4f}")
    mi, pi_, _ = paired(real, "mean_indicator", "mean_impute"); exi = ((real["mean_indicator"] - real["mean_impute"]) - (null["mean_indicator"] - null["mean_impute"])).dropna(); print(f"    indicator-impute    {mi:+.4f} p={pi_:.2g}; excess over null {float(np.median(exi)):+.4f}")
    print(f"  held: {[k for k, x in v.items() if x]}  failed: {[k for k, x in v.items() if not x]}")

if __name__ == "__main__":
    main(sys.argv[1])
