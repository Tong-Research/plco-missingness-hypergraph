"""Probe 9 (MIMIC DEV half): variant C, shrunk test-time projection (experiments/idea_h_projection.py).
A: probe 7's reduced-panel drops. B: probe 6's units 0 and 5 (leave-one-unit-out). Arms: tuned indicator, ours
(published), ours_C at kappa_proj in {20, 100, 500}. Reports AUPRC and the projection routes taken."""
import numpy as np, pathlib, time, warnings, sys; warnings.simplefilter("ignore")
sys.path.insert(0, "experiments"); sys.path.insert(0, "src")
from mimic_split import dev_mask
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegressionCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from hgmiss.estimator import HypergraphShrinkage
from run_h1_h4 import _median_support_kappa
from idea_h_projection import project_unseen
z = np.load(pathlib.Path.home()/".cache/phd-matrices/mimic4_sites.npz", allow_pickle=True)
X, y, g = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int), np.asarray(z["g"]).ravel(); cols = [str(c) for c in z["cols"]]
m = dev_mask(len(X)); X, y, g = X[m], y[m], g[m]
KP = [20, 100, 500]
def fit_all(Xtr, ytr):
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr)
    A = np.hstack([imp.transform(Xtr), np.isnan(Xtr)]); sc = StandardScaler().fit(A)
    lr = LogisticRegressionCV(Cs=8, cv=3, max_iter=2000, scoring="average_precision").fit(sc.transform(A), ytr)
    est = HypergraphShrinkage(kappa=1.0).fit(Xtr, ytr)
    k = _median_support_kappa([])({e: est.supports_[e] for e in est.patterns_}); est = HypergraphShrinkage(kappa=k).fit(Xtr, ytr)
    return {"t_indic": lambda Xt: lr.predict_proba(sc.transform(np.hstack([imp.transform(Xt), np.isnan(Xt)])))[:, 1],
            "ours": lambda Xt: est.predict_proba(Xt)}, est, k
def evaluate(Xtr, ytr, Xte, yte, fits, est):
    res = {kname: average_precision_score(yte, f(Xte)) for kname, f in fits.items()}; routes = ""
    for kp in KP:
        pe = project_unseen(est, Xte, Xtr, ytr, kappa_proj=kp); res[f"C{kp}"] = average_precision_score(yte, pe.predict_proba(Xte))
        if not routes:
            lg = pe.projection_log_; routes = f"proj {len(lg)} sets: anc {sum(v[0]=='ancestors' for v in lg.values())} sup {sum(v[0]=='supersets' for v in lg.values())} nomatch {pe.no_match_rate:.2f}"
    return res, routes
t0 = time.time()
print("=== A: reduced panel (train 70% dev, drop a lab at test) ===")
tr, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y, random_state=0)
fits, est, k = fit_all(X[tr], y[tr]); print(f"  kappa (median support) = {k:.0f}; fitted patterns {len(est.patterns_)}")
base, _ = evaluate(X[tr], y[tr], X[te], y[te], fits, est); print("  baseline: " + " ".join(f"{a} {v:.4f}" for a, v in base.items()))
obs_rate = (~np.isnan(X[tr])).mean(0); top = np.argsort(-obs_rate)[:6]
for j in list(top) + ["all"]:
    Xd = X[te].copy()
    if j == "all": Xd[:, top] = np.nan; name = "all six"
    else: Xd[:, j] = np.nan; name = cols[j][:16]
    res, routes = evaluate(X[tr], y[tr], Xd, y[te], fits, est)
    print(f"  {name:>16s} | " + " ".join(f"{a} {res[a]:.4f}" for a in res) + f" | {routes} [{time.time()-t0:.0f}s]", flush=True)
print("=== B: leave-one-unit-out, units 0 and 5 ===")
for u in [0, 5]:
    trm, tem = g != u, g == u
    fits, est, k = fit_all(X[trm], y[trm]); res, routes = evaluate(X[trm], y[trm], X[tem], y[tem], fits, est)
    print(f"  unit {u} n_te {int(tem.sum())} kappa {k:.0f} | " + " ".join(f"{a} {res[a]:.4f}" for a in res) + f" | {routes} [{time.time()-t0:.0f}s]", flush=True)
