"""Pre-registered reduced-panel test (prereg/PROJECTION.md, approved 2026-09-03 19:23).

HOLDOUT halves only (the complement of the hash split used by every Idea H probe). Per dataset: 70/30 stratified
split (seed 0) of the holdout half; fit six arms once on the 70 %; score the 30 % as is and with each of the six
most-observed training variables set to missing in turn, then all six. Writes one CSV row per (dataset, drop, arm)
to results/ideas/PROJ/<dataset>.csv plus the prevalence-only AUPRC (= prevalence) for P1.
"""
import hashlib, pathlib, sys, time, warnings
import numpy as np, pandas as pd
warnings.simplefilter("ignore")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "src"))
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from hgmiss.baselines.pattern import pattern_submodels
from hgmiss.estimator import HypergraphShrinkage
from run_h1_h4 import _median_support_kappa
from idea_h_projection import project_unseen
OUT = HERE.parent / "results" / "ideas" / "PROJ"; OUT.mkdir(parents=True, exist_ok=True)
CACHE = pathlib.Path.home() / ".cache" / "phd-matrices"

def holdout(name):
    z = np.load(CACHE / f"{name}_sites.npz", allow_pickle=True)
    X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); cols = [str(c) for c in z["cols"]]
    dev = np.array([int(hashlib.sha1(f"{name}-{i}".encode()).hexdigest(), 16) % 2 == 0 for i in range(len(X))])
    return X[~dev], y[~dev], cols

def run(name):
    X, y, cols = holdout(name); t0 = time.time()
    tr, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y, random_state=0)
    Xtr, ytr = X[tr], y[tr]
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr)
    def mk(ind):
        A = imp.transform(Xtr); A = np.hstack([A, np.isnan(Xtr)]) if ind else A; sc = StandardScaler().fit(A)
        lr = LogisticRegressionCV(Cs=8, cv=3, max_iter=2000, scoring="average_precision").fit(sc.transform(A), ytr)
        return lambda Xt: lr.predict_proba(sc.transform(np.hstack([imp.transform(Xt), np.isnan(Xt)]) if ind else imp.transform(Xt)))[:, 1]
    tree = HistGradientBoostingClassifier(random_state=0).fit(Xtr, ytr)
    est0 = HypergraphShrinkage(kappa=1.0).fit(Xtr, ytr)
    kappa = _median_support_kappa([])({e: est0.supports_[e] for e in est0.patterns_}); est = HypergraphShrinkage(kappa=kappa).fit(Xtr, ytr)
    arms = {"mean_impute": mk(False), "mean_indicator": mk(True), "histgb_native": lambda Xt: tree.predict_proba(Xt)[:, 1],
            "pattern_submodels": lambda Xt: pattern_submodels(Xtr, ytr, Xt), "ours": lambda Xt: est.predict_proba(Xt),
            "ours_projected": lambda Xt: project_unseen(est, Xt, Xtr, ytr, kappa_proj=kappa).predict_proba(Xt)}
    obs = (~np.isnan(Xtr)).mean(0); top = list(np.argsort(-obs)[:6])
    drops = [("none", [])] + [(cols[j], [j]) for j in top] + [("all_six", top)]
    rows = []
    print(f"  {name}: holdout n={len(y):,} train {len(tr):,} test {len(te):,} prev {y[te].mean():.4f} kappa {kappa:.0f} patterns {len(est.patterns_)}", flush=True)
    for dname, js in drops:
        Xd = X[te].copy(); Xd[:, js] = np.nan
        for a, f in arms.items():
            rows.append(dict(dataset=name, drop=dname, obs_rate=float(obs[js[0]]) if len(js) == 1 else float("nan"),
                             arm=a, auprc=float(average_precision_score(y[te], f(Xd))), prevalence=float(y[te].mean())))
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
        print(f"    {dname:>14s} " + " ".join(f"{r['arm'][:6]} {r['auprc']:.4f}" for r in rows[-len(arms):]) + f"  [{time.time()-t0:.0f}s]", flush=True)

if __name__ == "__main__":
    for name in sys.argv[1:] or ["mimic4", "eicu"]:
        run(name)
