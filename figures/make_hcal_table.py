"""tables/hcal.tex from results/hcal/*.csv (prereg/HCAL.md). One row per dataset: tree AUPRC; paired median delta of the kappa=0
per-pattern Platt and of the hierarchical Platt (with Wilcoxon p for the latter); paired median log-loss deltas for both; kappa range.
Also tables/hcal_counts.tex with \\HcalN, \\HcalNeverWorse, \\HcalLogloss, \\HcalKzeroHarm, \\HcalRankWin, \\HcalRoadSafety."""
import json, pathlib, collections, csv, numpy as np
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parents[1]
names = {f"sweep_{x['did']}": x["name"] for x in json.load(open(ROOT / "results/sweep_list.json"))}
names.update({"cand_higgs": "ATLAS Higgs", "cand_porto": "Porto Seguro", "cand_acs_income": "ACS income", "cand_airbnb": "Airbnb listings", "cand_nhanes": "NHANES mortality", "cand_mimic4_regime": "MIMIC-IV regimes", "mimic4": "MIMIC-IV first stays"})
npat = {r["dataset"]: int(float(r["n_pat"])) for r in csv.DictReader(open(ROOT / "results/screen_candidates.csv"))}
def _npat_holdout(key):
    """Distinct observed patterns in the holdout rows the runner used (cap 60,000, generator seed 0); used when the screen has no count."""
    import sys; sys.path.insert(0, str(ROOT / "experiments")); from run_hcal import load
    X, _ = load(key, "holdout", 60_000); return len({r.tobytes() for r in ~np.isnan(X)})
rows = []
for f in sorted((ROOT / "results/hcal").glob("*.csv")):
    by = collections.defaultdict(dict)
    for r in csv.DictReader(open(f)): by[r["arm"]][(r["seed"], r["fold"])] = r
    cells = sorted(by["tree"]); assert all(len(by[a]) == len(cells) for a in by), f
    def pm(arm, m):
        d = np.array([float(by[arm][c][m]) - float(by["tree"][c][m]) for c in cells]); return float(np.median(d)), (float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0)
    ds = f.stem; ks = sorted({int(by["hier_cv"][c]["kappa"]) for c in cells})
    rows.append(dict(key=ds, name=names.get(ds, ds), npat=npat.get(ds) or _npat_holdout(ds), tree=float(np.mean([float(by["tree"][c]["auprc"]) for c in cells])),
                     k0=pm("pattern_k0", "auprc")[0], hier=pm("hier_cv", "auprc")[0], hier_p=pm("hier_cv", "auprc")[1],
                     k0_ll=pm("pattern_k0", "logloss")[0], hier_ll=pm("hier_cv", "logloss")[0], hier_ll_p=pm("hier_cv", "logloss")[1], kmin=ks[0], kmax=ks[-1]))
n = len(rows); never = sum(r["hier"] >= -0.002 for r in rows); ll = sum(r["hier_ll"] < 0 and r["hier_ll_p"] < 0.05 for r in rows)
harm = sum(r["k0"] < -0.005 and r["hier"] >= -0.002 for r in rows); win = sum(r["hier"] > 0 and r["hier_p"] < 0.05 for r in rows)
rs = next((r for r in rows if r["key"] == "sweep_42739"), None)
def fk(k): return f"$10^{{{int(np.log10(k))}}}$"
def fp(x): return f"{(0.0 if abs(x) < 5e-5 else x):+.4f}"   # no signed zeros in the table
lines = [r"\begin{table}[t]", r"\centering", r"\caption{The shrinkage rule as a recalibration wrapper around a fixed native missing-value tree (holdout halves; pre-registered; datasets ordered by pattern count after the fact). Paired medians over $3 \times 5$ cells of each wrapper minus the tree; lower log-loss is better. $\kappa = 0$ is per-pattern Platt scaling without shrinkage; the hierarchical wrapper penalises each pattern's two Platt parameters toward its largest immediate ancestor's with weight $\kappa/n_e$, $\kappa$ by inner cross-validation, whose range over the 15 cells is the last column. Bold (hierarchical columns only): $p<0.05$, Wilcoxon. Text comparisons use unrounded medians. Two datasets with tree AUPRC $1.000$ are uninformative.}",
         r"\label{tab:hcal}", r"\setlength{\tabcolsep}{4pt}", r"\begin{tabular}{lrrrrrrl}", r"\toprule",
         r"Dataset & patterns & tree & \multicolumn{2}{c}{$\Delta$ AUPRC} & \multicolumn{2}{c}{$\Delta$ log-loss} & $\kappa$ \\",
         r" & & AUPRC & $\kappa=0$ & hier. & $\kappa=0$ & hier. & \\", r"\midrule"]
for r in sorted(rows, key=lambda r: -r["npat"]):
    nm = r["name"][:22].replace("_", r"\_"); h = fp(r["hier"]); hl = fp(r["hier_ll"])
    if r["hier_p"] < 0.05: h = r"\textbf{" + h + "}"
    if r["hier_ll_p"] < 0.05: hl = r"\textbf{" + hl + "}"
    kr = fk(r["kmin"]) if r["kmin"] == r["kmax"] else f"{fk(r['kmin'])}--{fk(r['kmax'])}"
    lines.append(f"{nm} & {r['npat']:,} & {r['tree']:.3f} & {fp(r['k0'])} & {h} & {fp(r['k0_ll'])} & {hl} & {kr} \\\\")
lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
(ROOT / "tables/hcal.tex").write_text("\n".join(lines) + "\n")
(ROOT / "tables/hcal_counts.tex").write_text("".join([f"\\newcommand{{\\HcalN}}{{{n}}}\n", f"\\newcommand{{\\HcalNeverWorse}}{{{never}}}\n", f"\\newcommand{{\\HcalLogloss}}{{{ll}}}\n", f"\\newcommand{{\\HcalKzeroHarm}}{{{harm}}}\n", f"\\newcommand{{\\HcalRankWin}}{{{win}}}\n",
    f"\\newcommand{{\\HcalRoadSafety}}{{{rs['hier']:+.3f}}}\n" if rs else "", f"\\newcommand{{\\HcalRoadSafetyKzero}}{{{rs['k0']:+.3f}}}\n" if rs else ""]))
print(f"{n} datasets; never worse {never}; log-loss win {ll}; k0 harmful & hier safe {harm}; rank win {win}")
for r in sorted(rows, key=lambda r: -r["npat"]): print(f"  {r['name'][:22]:22s} pat {r['npat']:6d} tree {r['tree']:.3f} k0 {r['k0']:+.4f} hier {r['hier']:+.4f} (p {r['hier_p']:.2g}) ll k0 {r['k0_ll']:+.4f} hier {r['hier_ll']:+.4f} (p {r['hier_ll_p']:.2g})")
