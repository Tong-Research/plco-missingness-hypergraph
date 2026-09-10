"""Probe 8 (eICU DEV half): leave-one-hospital-out over hospitals with >= 400 dev records. Arms as probe 6 (no projection)."""
import numpy as np, pathlib, hashlib, time, warnings, sys; warnings.simplefilter("ignore")
sys.path.insert(0, "experiments"); sys.path.insert(0, "src")
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from hgmiss.baselines.pattern import pattern_submodels
from hgmiss import estimator
from run_h1_h4 import _median_support_kappa
import scipy.stats as st
z = np.load(pathlib.Path.home()/".cache/phd-matrices/eicu_sites.npz", allow_pickle=True); X, y, g = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int), np.asarray(z["g"]).ravel()
dev = np.array([int(hashlib.sha1(f"eicu-{i}".encode()).hexdigest(), 16) % 2 == 0 for i in range(len(X))]); X, y, g = X[dev], y[dev], g[dev]
def tuned(Xtr, ytr, Xte, indicator):
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr); A, B = imp.transform(Xtr), imp.transform(Xte)
    if indicator: A = np.hstack([A, np.isnan(Xtr)]); B = np.hstack([B, np.isnan(Xte)])
    sc = StandardScaler().fit(A); return LogisticRegressionCV(Cs=6, cv=3, max_iter=1000, scoring="average_precision").fit(sc.transform(A), ytr).predict_proba(sc.transform(B))[:, 1]
arms = {"t_impute": lambda a, b, c: tuned(a, b, c, False), "t_indic": lambda a, b, c: tuned(a, b, c, True), "tree": lambda a, b, c: HistGradientBoostingClassifier(random_state=0).fit(a, b).predict_proba(c)[:, 1], "submod": pattern_submodels, "ours": estimator.fit_predict(kappa=_median_support_kappa([]))}
units, counts = np.unique(g, return_counts=True); big = units[counts >= 400]; print(f"eICU dev n={len(X):,}; hospitals with >= 400 dev records: {len(big)}")
t0 = time.time(); rows = []
print(f"{'hosp':>5s} {'n_te':>5s} {'prev':>5s} {'shift':>5s} {'rare':>5s} | " + " ".join(f"{k:>8s}" for k in arms) + "   ours-t_indic")
for u in big:
    tr, te = g != u, g == u
    if y[te].sum() < 10: continue
    Mtr, Mte = np.isnan(X[tr]), np.isnan(X[te]); shift = float(np.abs(Mtr.mean(0) - Mte.mean(0)).mean())
    cnt = {}
    for r in (~Mtr): k = r.tobytes(); cnt[k] = cnt.get(k, 0) + 1
    rare = float(np.mean([cnt.get(r.tobytes(), 0) < 30 for r in (~Mte)]))
    res = {}
    for k, fn in arms.items():
        try: res[k] = average_precision_score(y[te], fn(X[tr], y[tr], X[te]))
        except Exception: res[k] = np.nan
    rows.append((u, res, shift, rare)); print(f"{int(u):5d} {int(te.sum()):5d} {y[te].mean():5.3f} {shift:5.3f} {rare:5.2f} | " + " ".join(f"{res[k]:8.4f}" for k in arms) + f"   {res['ours']-res['t_indic']:+.4f}   [{time.time()-t0:.0f}s]", flush=True)
print("  mean over hospitals: " + " ".join(f"{k} {np.nanmean([r[1][k] for r in rows]):.4f}" for k in arms))
d = np.array([r[1]["ours"] - r[1]["t_indic"] for r in rows]); dt = np.array([r[1]["ours"] - r[1]["tree"] for r in rows]); sh = np.array([r[2] for r in rows])
print(f"  ours−t_indic: median {np.median(d):+.4f}, wins {int((d>0).sum())}/{len(d)}, Wilcoxon p={st.wilcoxon(d).pvalue:.3g}; corr(shift, .) {st.spearmanr(sh, d)[0]:+.2f}")
print(f"  ours−tree:    median {np.median(dt):+.4f}, wins {int((dt>0).sum())}/{len(dt)}, Wilcoxon p={st.wilcoxon(dt).pvalue:.3g}; corr(shift, .) {st.spearmanr(sh, dt)[0]:+.2f}")
