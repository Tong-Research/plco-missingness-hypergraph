"""Idea B (2026-09-04): hierarchical residual boosting on the missingness hypergraph. DEV-HALF PROBE ONLY.

Patterns = realised observed sets with >= min_support own rows. Hierarchy = immediate ancestors among fitted patterns
(hgmiss.patterns.immediate_ancestors). Root patterns (no fitted ancestor) get a LightGBM model on their SUPPORT rows
(every row observing their variables) -- the shared base. Every other pattern gets a LightGBM correction of `n_corr`
trees fitted on its OWN rows with init_score = its parent's log-odds (parent = the immediate ancestor of largest
support; the parent's columns are a subset of the child's, so it is defined on every child row). n_corr is the one
knob: 0 = every pattern uses its ancestor chain unchanged; large = independent trees per pattern.
Prediction: a record uses its own pattern if fitted, else the largest fitted pattern contained in its observed set
(deepest ancestor), else the prior. No collapse.
"""
import numpy as np, lightgbm as lgb
from scipy.special import logit, expit
from hgmiss.patterns import immediate_ancestors

class HierBoost:
    def __init__(self, n_corr=30, n_root=200, min_support=30, lr=0.1, leaves=15, min_child=20):
        self.n_corr, self.n_root, self.min_support, self.lr, self.leaves, self.min_child = n_corr, n_root, min_support, lr, leaves, min_child
    def _lgb(self, n): return dict(n_estimators=n, learning_rate=self.lr, num_leaves=self.leaves, min_child_samples=self.min_child, verbose=-1, n_jobs=4)
    def fit(self, X, y):
        X = np.asarray(X, float); y = np.asarray(y).ravel(); mask = ~np.isnan(X); self.prior_ = float(y.mean())
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; rows_of = {}
        for i, e in enumerate(keys): rows_of.setdefault(e, []).append(i)
        self.patterns_ = sorted([e for e, r in rows_of.items() if e and len(r) >= self.min_support and len(np.unique(y[r])) == 2], key=len)
        self.support_ = {e: int(mask[:, sorted(e)].all(1).sum()) for e in self.patterns_}
        anc = immediate_ancestors(self.patterns_); self.parent_, self.model_, self.cols_ = {}, {}, {}
        for e in self.patterns_:
            cols = sorted(e); self.cols_[e] = cols; parents = [a for a in anc.get(e, []) if a in self.model_]
            if not parents:
                rows = np.flatnonzero(mask[:, cols].all(1)); m = lgb.LGBMClassifier(**self._lgb(self.n_root)).fit(X[np.ix_(rows, cols)], y[rows]); self.model_[e] = ("root", m); continue
            p = max(parents, key=lambda a: self.support_[a]); self.parent_[e] = p; rows = np.array(rows_of[e])
            if self.n_corr == 0: self.model_[e] = ("inherit", None); continue
            off = self._logit(p, X[rows]); m = lgb.LGBMClassifier(**self._lgb(self.n_corr)).fit(X[np.ix_(rows, cols)], y[rows], init_score=off); self.model_[e] = ("corr", m)
        self._fitted = set(self.model_); return self
    def _logit(self, e, Xrows):
        kind, m = self.model_[e]; cols = self.cols_[e]
        if kind == "root": return m.predict_proba(Xrows[:, cols], raw_score=True)
        base = self._logit(self.parent_[e], Xrows)
        return base if kind == "inherit" else base + m.predict_proba(Xrows[:, cols], raw_score=True)
    def predict_proba(self, X):
        X = np.asarray(X, float); mask = ~np.isnan(X); out = np.full(len(X), self.prior_); cache = {}; self.route_ = {"own": 0, "ancestor": 0, "prior": 0}
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; groups = {}
        for i, e in enumerate(keys): groups.setdefault(e, []).append(i)
        for e, idx in groups.items():
            if e in self._fitted: tgt, route = e, "own"
            else:
                subs = [p for p in self.patterns_ if p < e]; tgt = max(subs, key=lambda p: (len(p), self.support_[p])) if subs else None; route = "ancestor" if subs else "prior"
            self.route_[route] += len(idx)
            if tgt is not None: out[idx] = expit(self._logit(tgt, X[idx]))
        return np.clip(out, 1e-6, 1 - 1e-6)
