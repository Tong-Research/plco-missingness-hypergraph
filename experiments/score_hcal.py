"""Score HCAL runs: per dataset, paired (cell-wise) differences of each arm against the tree, median and Wilcoxon p, on AUPRC,
log-loss and small-pattern log-loss; then the pre-registered verdict per prediction. Usage: score_hcal.py results/hcal/*.csv"""
import sys, csv, collections, numpy as np
from scipy import stats
def load(paths):
    rows = []
    for p in paths: rows += list(csv.DictReader(open(p)))
    return rows
def main(paths):
    rows = load(paths); by = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows: by[(r["dataset"], r["slice"])][r["arm"]][(r["seed"], r["fold"])] = r
    print(f"{'dataset':22s} {'slice':7s} cells | AUPRC d-med (p) hier | k0 | logloss d-med hier | k0 | small-ll d-med hier | k0 | kappas")
    verdict = {}
    for (ds, sl), arms in sorted(by.items()):
        cells = sorted(arms["tree"]); out = [ds, sl, len(cells)]
        def paired(arm, m):
            d = np.array([float(arms[arm][c][m]) - float(arms["tree"][c][m]) for c in cells if c in arms[arm]]); d = d[~np.isnan(d)]
            return np.median(d), (stats.wilcoxon(d).pvalue if len(d) >= 5 and np.any(d != 0) else np.nan)
        res = {}
        for m in ["auprc", "logloss", "small_logloss"]:
            for arm in ["hier_cv", "pattern_k0"]: res[(m, arm)] = paired(arm, m)
        ks = sorted(set(arms["hier_cv"][c]["kappa"] for c in cells if c in arms["hier_cv"]))
        print(f"{ds:22s} {sl:7s} {len(cells):5d} | {res[('auprc','hier_cv')][0]:+.4f} ({res[('auprc','hier_cv')][1]:.2g}) | {res[('auprc','pattern_k0')][0]:+.4f} | {res[('logloss','hier_cv')][0]:+.4f} | {res[('logloss','pattern_k0')][0]:+.4f} | {res[('small_logloss','hier_cv')][0]:+.4f} | {res[('small_logloss','pattern_k0')][0]:+.4f} | {ks}")
        verdict[ds] = res
    n = len(verdict)
    p1 = sum(1 for r in verdict.values() if r[("auprc", "hier_cv")][0] >= -0.002)
    p2 = sum(1 for r in verdict.values() if r[("logloss", "hier_cv")][0] < 0 and (r[("logloss", "hier_cv")][1] < 0.05))
    p3 = sum(1 for r in verdict.values() if r[("logloss", "hier_cv")][0] <= r[("logloss", "pattern_k0")][0])
    p4 = sum(1 for r in verdict.values() if r[("auprc", "hier_cv")][0] > 0 and r[("auprc", "hier_cv")][1] < 0.05)
    print(f"\nP1 never worse in AUPRC (median >= -0.002): {p1}/{n}\nP2 log-loss below the tree, p<0.05: {p2}/{n}\nP3 log-loss <= kappa=0 ablation: {p3}/{n}\nP4 AUPRC above the tree, p<0.05: {p4}/{n}")
if __name__ == "__main__": main(sys.argv[1:])
