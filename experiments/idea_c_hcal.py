"""Idea C (2026-09-04): pattern-hierarchical calibration and shrinkage of ANY base model's outputs (dev-half probe).

Wrap a fitted base model (here the tuned native tree). Using out-of-fold logits on the training fold, fit for every
realised pattern e a Platt recalibration logit' = a_e + b_e * logit, and shrink (a_e, b_e) toward the parent's
(a_p, b_p) with lambda_e = n_e / (n_e + kappa), parents in containment order, exactly the published shrinkage rule
applied to calibration parameters instead of regression coefficients. kappa by inner CV on log-loss. A test pattern
never seen uses its deepest fitted ancestor's (a, b); the root falls back to the global Platt fit.
Claims tested: (1) pooled AUPRC unchanged or better; (2) Brier / log-loss improve; (3) calibration inside small
patterns (support < 300) improves; (4) the tree's small-pattern ranking improves. Nothing here is linear, and the
wrapper is model-agnostic."""
import numpy as np
from scipy.special import expit, logit as _logit
from scipy.optimize import minimize
from sklearn.model_selection import StratifiedKFold
from hgmiss.patterns import immediate_ancestors

def _platt(z, y, prior=(0.0, 1.0), w=0.0):
    """Minimise log-loss of sigmoid(a + b z) with an L2 pull of strength w toward the prior (a0, b0)."""
    a0, b0 = prior
    def f(t):
        a, b = t; p = np.clip(expit(a + b * z), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)) + w * ((a - a0) ** 2 + (b - b0) ** 2)
    return tuple(minimize(f, x0=np.array(prior), method="L-BFGS-B").x)

class HierCalibrator:
    def __init__(self, kappa=100.0, min_support=30): self.kappa, self.min_support = kappa, min_support
    def fit(self, z_oof, y, mask):
        """z_oof: out-of-fold logits of the base model on the training rows; mask: observed indicator."""
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; rows = {}
        for i, e in enumerate(keys): rows.setdefault(e, []).append(i)
        self.global_ = _platt(z_oof, y); pats = sorted([e for e, r in rows.items() if e and len(r) >= self.min_support and len(np.unique(y[r])) == 2], key=len)
        anc = immediate_ancestors(pats); self.params_ = {}; self.n_ = {e: len(rows[e]) for e in pats}
        for e in pats:
            parents = [p for p in anc.get(e, []) if p in self.params_]
            prior = self.params_[max(parents, key=lambda p: self.n_[p])] if parents else self.global_
            n = self.n_[e]; w = self.kappa / max(n, 1)   # pull strength: kappa/n -> lambda = n/(n+kappa) in the quadratic limit
            r = np.array(rows[e]); self.params_[e] = _platt(z_oof[r], y[r], prior=prior, w=w)
        self.patterns_ = pats; return self
    def transform(self, z, mask):
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; out = np.empty(len(z)); cache = {}
        for i, e in enumerate(keys):
            if e not in cache:
                if e in self.params_: cache[e] = self.params_[e]
                else:
                    subs = [p for p in self.patterns_ if p < e]; cache[e] = self.params_[max(subs, key=lambda p: (len(p), self.n_[p]))] if subs else self.global_
            a, b = cache[e]; out[i] = expit(a + b * z[i])
        return np.clip(out, 1e-6, 1 - 1e-6)

def _guarded_fit_predict(make_model, Xt, yt, Xv):
    """HistGradientBoosting raises 'window shape cannot be larger than input array shape' when a column has almost no
    observed values in the fit rows (its binning subsample is empty). First try the plain fit, so runs that never hit the
    error are unchanged; on that error drop columns with fewer than two observed values in Xt and refit (2026-09-04)."""
    try:
        return make_model().fit(Xt, yt).predict_proba(Xv)[:, 1]
    except ValueError as e:
        if "window shape" not in str(e): raise
        kc = np.flatnonzero(np.array([len(np.unique(Xt[~np.isnan(Xt[:, j]), j])) >= 2 for j in range(Xt.shape[1])]))
        return make_model().fit(Xt[:, kc], yt).predict_proba(Xv[:, kc])[:, 1]

def oof_logits(make_model, X, y, n_splits=3, seed=0):
    z = np.empty(len(y))
    for t, v in StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(X, y):
        p = _guarded_fit_predict(make_model, X[t], y[t], X[v]); z[v] = _logit(np.clip(p, 1e-6, 1 - 1e-6))
    return z
