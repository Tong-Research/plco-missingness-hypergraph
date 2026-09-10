"""Score prereg/PROJECTION.md from results/ideas/PROJ/{mimic4,eicu}.csv. Refuses incomplete files."""
import pathlib, sys
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; D = HERE.parent / "results" / "ideas" / "PROJ"
ARMS = ["mean_impute", "mean_indicator", "histgb_native", "pattern_submodels", "ours", "ours_projected"]

def main():
    verdict = {"P1": True, "P2": True, "P3": True, "P4": True}
    for name in ["mimic4", "eicu"]:
        f = D / f"{name}.csv"
        if not f.exists(): raise SystemExit(f"  {f} MISSING -- refusing to score")
        d = pd.read_csv(f); piv = d.pivot_table(index="drop", columns="arm", values="auprc")
        if len(piv) != 8 or set(ARMS) - set(piv.columns): raise SystemExit(f"  {name}: {len(piv)} of 8 drops -- incomplete, refusing")
        prev = float(d["prevalence"].iloc[0]); base = piv.loc["none"]
        obs = d.groupby("drop")["obs_rate"].first()
        print(f"  {name}: prevalence {prev:.4f}  baseline " + " ".join(f"{a} {base[a]:.4f}" for a in ARMS))
        for drop in [r for r in piv.index if r != "none"]:
            r = piv.loc[drop]; universal = (drop == "all_six") or (obs[drop] >= 0.99)
            p1 = (abs(r["ours"] - prev) <= 0.01) if universal else None
            p2 = (r["ours_projected"] >= r["mean_indicator"] - 0.03) and (r["ours_projected"] >= base["ours"] - 0.02)
            p4 = r["ours_projected"] <= r["mean_indicator"] + 0.005
            if p1 is False: verdict["P1"] = False
            verdict["P2"] &= p2; verdict["P4"] &= p4
            print(f"    {drop:>14s} obs {obs[drop] if drop != 'all_six' else float('nan'):5.3f} | ours {r['ours']:.4f} proj {r['ours_projected']:.4f} indic {r['mean_indicator']:.4f} tree {r['histgb_native']:.4f} sub {r['pattern_submodels']:.4f} imp {r['mean_impute']:.4f} | "
                  f"P1 {'n/a' if p1 is None else p1}  P2 {p2}  P4 {p4}")
        p3 = abs(base["ours_projected"] - base["ours"]) <= 0.002; verdict["P3"] &= p3
        print(f"    P3 in-distribution |proj - ours| = {abs(base['ours_projected'] - base['ours']):.4f}  {p3}")
    held = [k for k, v in verdict.items() if v]; failed = [k for k, v in verdict.items() if not v]
    print(f"\n  held: {held}   failed: {failed}")
    if not verdict["P1"]: print("  OUTCOME: withdrawal (a) -- the collapse is not general; C2 stays an engineering note.")
    elif not verdict["P2"]: print("  OUTCOME: withdrawal (b) -- the fix is incomplete; report the failing drop and route.")
    elif not verdict["P3"]: print("  OUTCOME: withdrawal (c) -- the projection changes in-distribution behaviour.")
    else: print("  OUTCOME: limitation and fix both hold" + ("" if verdict["P4"] else " -- but P4 failed: the projection beat the indicator somewhere; report, do not sell"))

if __name__ == "__main__":
    sys.exit(main())
