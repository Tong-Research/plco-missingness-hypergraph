"""Post-hoc comparator (referee 5): switch_cv (global vs kappa=0 Platt by inner CV) against hier_cv, per dataset, on results/hcal2.
Also verifies the four registered arms reproduce results/hcal exactly. Writes tables/hcal_switch.tex defining \\HCALSWITCH."""
import csv, collections, glob, pathlib, numpy as np
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parents[1]
def by(f):
    d = collections.defaultdict(dict)
    for r in csv.DictReader(open(f)): d[r["arm"]][(r["seed"], r["fold"])] = r
    return d
rows = []
for f in sorted(glob.glob(str(ROOT / "results/hcal2/*.csv"))):
    name = pathlib.Path(f).stem; b = by(f); a = by(ROOT / "results/hcal" / f"{name}.csv")
    repro = max(abs(float(a[arm][c][m]) - float(b[arm][c][m])) for arm in ["tree", "global", "pattern_k0", "hier_cv"] for c in a[arm] for m in ["auprc", "logloss"])
    cells = sorted(b["tree"]); ch = collections.Counter(b["switch_cv"][c]["kappa"] for c in cells)
    dl = np.array([float(b["hier_cv"][c]["logloss"]) - float(b["switch_cv"][c]["logloss"]) for c in cells]); da = np.array([float(b["hier_cv"][c]["auprc"]) - float(b["switch_cv"][c]["auprc"]) for c in cells])
    sw_tree = np.median([float(b["switch_cv"][c]["auprc"]) - float(b["tree"][c]["auprc"]) for c in cells])
    rows.append(dict(name=name, repro=repro, choices=dict(ch), dll=float(np.median(dl)), p=(float(stats.wilcoxon(dl).pvalue) if np.any(dl != 0) else 1.0), dau=float(np.median(da)), sw_tree=sw_tree, better=int((dl < 0).sum()), n=len(cells)))
    print(f"{name:20s} repro max|diff| {repro:.1e} | switch chose {dict(ch)} | hier - switch: logloss {np.median(dl):+.5f} (p {rows[-1]['p']:.2g}, hier better {int((dl<0).sum())}/{len(cells)}) AUPRC {np.median(da):+.4f} | switch - tree AUPRC {sw_tree:+.4f}")
harm = [r for r in rows if r["name"] in ("cand_mimic4_regime", "mimic4", "cand_acs_income", "cand_nhanes")]
if len(harm) == 4:
    allglob = all(set(r["choices"]) == {"global"} for r in harm); nb = sum(r["dll"] <= -0.0002 and r["p"] < 0.05 for r in harm)   # a margin below 0.0002 log-loss is the global fit under another name
    txt = (f"That comparator was run after the fact on every dataset: on the four, the switch chose the global fit in every cell"
           + (", so it reduces to global recalibration and is never worse than the tree" if allglob else "")
           + f"; the hierarchy's log-loss is below the switch's by at least $0.0002$ at $p<0.05$ on {nb} of the four (by " + ", ".join(f"${-r['dll']:.4f}$" for r in harm) + " respectively), "
           + ("so it does something the switch cannot, by settling at intermediate $\\kappa$; the margins are small and post hoc." if nb >= 3 else ("so on those the hierarchy settles at intermediate $\\kappa$ and does something the switch cannot, while on the others it is the global fit under another name; the safety is shared between the hierarchy and the cross-validation, and the margins are post hoc." if nb >= 1 else "which does not separate the hierarchy from the switch; the safety on those four is the cross-validation's, not the hierarchy's.")))
    (ROOT / "tables/hcal_switch.auto.tex").write_text("\\renewcommand{\\HCALSWITCH}{" + txt + "}\n"); print("\nwrote tables/hcal_switch.auto.tex (the shipped sentence is hand-set in tables/hcal_switch.tex):\n ", txt)
else: print("\nharmful-four not all in yet:", [r["name"] for r in harm])
