"""Variant X (2026-09-04, from the Higgs dev-half diagnosis): the hypergraph estimator with EXACT-ROW fits.

The published estimator fits pattern e on its support S(e) = rows observing every variable of e (a superset
rule), then scores a record by the support-weighted mean of every fitted pattern contained in its observed
set. When patterns are few, large and disjoint regimes (Higgs: jet multiplicities), the small patterns become
pooled models across regimes and the combine step lets them swamp the regime's own model: dev-half AUPRC
0.631 against 0.664 for imputation, while a per-pattern model on each pattern's OWN rows reaches 0.711.

Variant X keeps the hierarchy and the shrinkage rule but changes two things:
  (1) raw theta_e is fitted on the rows whose observed set EQUALS e (exact rows), for every realised pattern
      with >= min_support exact rows;
  (2) a record is scored by its own pattern's shrunk model when that pattern is fitted; otherwise by the
      support-weighted mean of its fitted immediate ancestors (the published rule, restricted to the
      nearest layer); otherwise the prior.
Shrinkage is unchanged: theta_e shrunk toward its immediate ancestors with lambda = n_e/(n_e + kappa), where
n_e is now the exact count. kappa = median exact support (same rule as published).
"""
import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from hgmiss.patterns import extract_patterns, immediate_ancestors
from hgmiss.shrinkage import INTERCEPT, shrink

class ExactHypergraph:
    def __init__(self, kappa="median", min_support=30):
        self.kappa, self.min_support = kappa, min_support

    def fit(self, X, y):
        X = np.asarray(X, float); y = np.asarray(y).ravel(); self.prior_ = float(y.mean())
        self.scaler_ = StandardScaler().fit(X); Xs = self.scaler_.transform(X); mask = ~np.isnan(X)
        realised = extract_patterns(mask)
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]
        rows_of = {}
        for i, e in enumerate(keys): rows_of.setdefault(e, []).append(i)
        self.patterns_ = [e for e, r in rows_of.items() if e and len(r) >= self.min_support and len(np.unique(y[r])) == 2]
        self.supports_ = {e: len(rows_of[e]) for e in self.patterns_}
        k = float(np.median(list(self.supports_.values()))) if self.kappa == "median" else float(self.kappa); self.kappa_ = k
        self.ancestors_ = immediate_ancestors(self.patterns_)
        raw = {}
        for e in self.patterns_:
            cols = sorted(e); r = rows_of[e]; lr = LogisticRegression(max_iter=2000).fit(Xs[np.ix_(r, cols)], y[r])
            raw[e] = {INTERCEPT: float(lr.intercept_[0]), **{v: float(c) for v, c in zip(cols, lr.coef_.ravel())}}
        self.raw_theta_ = raw; self.theta_ = shrink(raw, self.supports_, self.ancestors_, k); self._fitted = set(self.patterns_)
        return self

    def _score(self, th, xrow):
        return expit(th[INTERCEPT] + sum(th[v] * xrow[v] for v in th if v != INTERCEPT))

    def predict_proba(self, X):
        X = np.asarray(X, float); Xs = self.scaler_.transform(X); mask = ~np.isnan(X); out = np.empty(len(X)); self.route_ = {"exact": 0, "ancestors": 0, "prior": 0}
        cache = {}
        for i in range(len(X)):
            e = frozenset(np.flatnonzero(mask[i]).tolist())
            if e not in cache:
                if e in self._fitted: cache[e] = ("exact", [e])
                else:
                    subs = [p for p in self.patterns_ if p < e]; maximal = [p for p in subs if not any(p < q for q in subs)]
                    cache[e] = ("ancestors", maximal) if maximal else ("prior", [])
            route, pats = cache[e]; self.route_[route] += 1
            if route == "prior": out[i] = self.prior_; continue
            w = np.array([self.supports_[p] for p in pats], float); out[i] = float(np.dot(w / w.sum(), [self._score(self.theta_[p], Xs[i]) for p in pats]))
        return np.clip(out, 1e-6, 1 - 1e-6)
