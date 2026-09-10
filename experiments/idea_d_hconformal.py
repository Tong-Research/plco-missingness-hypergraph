"""Idea D (2026-09-04): mask-conditional conformal prediction sets via hierarchical pooling on the missingness hypergraph.
Binary classification, split conformal. Score s_i = 1 - p_hat(y_i | x_i) on a calibration set; a prediction set at level
1 - alpha contains every label whose score is <= q. Marginal conformal uses one quantile q for everyone; per-pattern
conformal uses q_e from the calibration rows of pattern e alone (invalid/undefined for small e); the HIERARCHICAL rule
uses for pattern e the calibration rows of e AND of its ancestors, with each ancestor row weighted by
lambda_e = n_e / (n_e + kappa) applied to the own rows and (1 - lambda_e) spread over ancestor rows -- a weighted quantile
(Tibshirani et al. 2019 style). Unseen test patterns use their deepest fitted ancestor's pooled set.
Metric: coverage per pattern (mean over test patterns of |coverage_e - (1-alpha)|, and the worst pattern), and average set
size, for marginal / per-pattern / hierarchical."""
import numpy as np
from hgmiss.patterns import immediate_ancestors

def wquantile(v, w, q):
    o = np.argsort(v); v, w = v[o], w[o]; c = np.cumsum(w) / w.sum(); return float(v[np.searchsorted(c, q, side="left").clip(0, len(v) - 1)])

class HierConformal:
    def __init__(self, alpha=0.1, kappa=100.0, min_support=30): self.alpha, self.kappa, self.min_support = alpha, kappa, min_support
    def fit(self, scores, mask):
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; rows = {}
        for i, e in enumerate(keys): rows.setdefault(e, []).append(i)
        n = len(scores); self.q_marg_ = float(np.quantile(scores, min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)))
        self.patterns_ = sorted([e for e, r in rows.items() if e and len(r) >= self.min_support], key=len); anc = immediate_ancestors(self.patterns_)
        self.rows_ = {e: np.array(rows[e]) for e in self.patterns_}; self.q_own_, self.q_hier_ = {}, {}
        # all ancestors (transitive) for pooling
        self.allanc_ = {}
        for e in self.patterns_:
            acc, stack = set(), list(anc.get(e, []))
            while stack:
                a = stack.pop()
                if a in acc: continue
                acc.add(a); stack.extend(anc.get(a, []))
            self.allanc_[e] = sorted(acc, key=len)
        for e in self.patterns_:
            r = self.rows_[e]; ne = len(r); self.q_own_[e] = float(np.quantile(scores[r], min(1.0, np.ceil((ne + 1) * (1 - self.alpha)) / ne)))
            lam = ne / (ne + self.kappa); pool = [a for a in self.allanc_[e]]
            if pool:
                arows = np.concatenate([self.rows_[a] for a in pool]); v = np.concatenate([scores[r], scores[arows]]); w = np.concatenate([np.full(ne, lam / ne), np.full(len(arows), (1 - lam) / len(arows))])
            else: v, w = scores[r], np.full(ne, 1.0 / ne)
            self.q_hier_[e] = wquantile(v, w, 1 - self.alpha)
        return self
    def _target(self, e):
        if e in self.q_hier_: return e
        subs = [p for p in self.patterns_ if p < e]; return max(subs, key=lambda p: (len(p), len(self.rows_[p]))) if subs else None
    def sets(self, p1, mask, rule):
        """Return, for each test row, whether label 0 and label 1 are in the set (n x 2 boolean)."""
        keys = [frozenset(np.flatnonzero(r).tolist()) for r in mask]; s0, s1 = p1, 1 - p1   # score of label 0 is 1 - P(y=0) = p1
        q = np.empty(len(p1))
        for i, e in enumerate(keys):
            if rule == "marginal": q[i] = self.q_marg_
            else:
                t = self._target(e); q[i] = self.q_marg_ if t is None else (self.q_own_[t] if rule == "own" else self.q_hier_[t])
        return np.stack([s0 <= q, s1 <= q], axis=1)
