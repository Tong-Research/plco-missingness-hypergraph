"""Shared pieces for the 2026-09-06 idea probes (RECOV, DISTIL, UNSEEN, AMPUTE/PROXY). Loader and tree config are the
HCAL ones so every probe sees the same holdout halves as Table sweep."""
import pathlib, sys, numpy as np, warnings
warnings.simplefilter("ignore")
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "src"))
from run_hcal import load, CFG                      # noqa: E402
from hgmiss.patterns import immediate_ancestors     # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier as HGB  # noqa: E402
from sklearn.impute import SimpleImputer            # noqa: E402
from sklearn.preprocessing import StandardScaler    # noqa: E402
from sklearn.linear_model import LogisticRegressionCV  # noqa: E402

def tree(seed=0, **kw):
    c = dict(CFG); c.update(kw); return HGB(random_state=seed, early_stopping=False, **c)

def keys(obs):
    """obs: boolean observed-indicator matrix -> one frozenset of observed column indices per row."""
    return [frozenset(np.flatnonzero(r).tolist()) for r in obs]

def groups(ks):
    d = {}
    for i, e in enumerate(ks): d.setdefault(e, []).append(i)
    return {e: np.array(v) for e, v in d.items()}

def tuned(Xtr, ytr, Xte, kind):
    """The three linear arms of results/cand (run_candidate.tuned, copied verbatim so this file imports nothing heavy)."""
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr); A, B = imp.transform(Xtr), imp.transform(Xte)
    Mtr, Mte = np.isnan(Xtr).astype(float), np.isnan(Xte).astype(float)
    if kind == "mean_indicator": A, B = np.hstack([A, Mtr]), np.hstack([B, Mte])
    if kind == "mask_interaction": A, B = np.hstack([A, Mtr, A * (1 - Mtr)]), np.hstack([B, Mte, B * (1 - Mte)])
    sc = StandardScaler().fit(A)
    return LogisticRegressionCV(Cs=6, cv=3, max_iter=2000, scoring="average_precision").fit(sc.transform(A), ytr).predict_proba(sc.transform(B))[:, 1]
