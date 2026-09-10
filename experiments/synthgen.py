"""Realistic synthetic data generator for structured-missingness experiments.

Design goals (and why each matters for external validity):

1. MECHANISM follows the standard taxonomy (Rubin 1976) and is generated with the
   *multivariate amputation* formalism of Schouten, Lugtig & Vink (2018,
   J. Stat. Comput. Simul. 88(15):2909-2930; the ``ampute`` function in ``mice``),
   which is pattern-based: one defines a set of missingness PATTERNS and assigns
   each row to a pattern via a weighted sum of its variables passed through a
   logistic link. That is exactly the object our estimator models, so we adopt it
   rather than ad-hoc per-cell dropping.
     - MCAR: pattern assignment independent of X and y.
     - MAR : assignment driven by variables that remain OBSERVED in that pattern.
     - MNAR: assignment driven by the variables the pattern HIDES.

2. PATTERN STRUCTURE is calibrated to real data. We measured 10 real tabular
   datasets with native missingness (PLCO cohorts, support2, hypothyroid, vote,
   heart-4site, colic, ...) and found they span a wide range of pattern
   concentration -- from a handful of dominant patterns (hypothyroid: 26 patterns,
   98% of rows in patterns of support >= 30) to near-unique patterns (colic: 225
   patterns for 368 rows, 0% of rows in a support->=30 pattern). ``concentration``
   interpolates over that measured range via a Zipf-like pattern-size law, so
   experiments can be run in the regime a target application actually occupies
   instead of only the flattering one.

3. FEATURES are correlated and mixed-type (a latent factor model plus skewed and
   binary marginals), because real clinical tables are neither independent nor
   Gaussian, and correlation is what lets an imputed value stand in for a missing
   one (the redundancy that made missingness uninformative on PLCO/MIMIC).

4. SIGNAL separates the two properties real data confounds:
     - ``info``: the pattern shifts the intercept (a base-rate main effect, which
       a mask-indicator model can absorb),
     - ``het`` : the pattern changes the feature->outcome SLOPES (only a
       pattern-conditional model can express this).

5. PREVALENCE is tunable to the clinical range (5-12% in our cohorts), because
   AUPRC and calibration behave very differently under class imbalance.

``dataset_stats`` returns the same descriptive statistics we computed on the real
data, so any generated dataset can be placed in the measured real-data range.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from scipy.special import expit


def _latent_features(rng, n, d, n_factors=3, skew_frac=0.25, binary_frac=0.2):
    """Correlated, mixed-type features via a latent factor model."""
    L = rng.normal(size=(n, n_factors))
    W = rng.normal(size=(n_factors, d)) * 0.8
    X = L @ W + rng.normal(size=(n, d))
    n_skew = int(round(skew_frac * d))
    n_bin = int(round(binary_frac * d))
    cols = rng.permutation(d)
    for j in cols[:n_skew]:                       # right-skewed (labs, counts)
        X[:, j] = np.exp(0.6 * X[:, j]) - 1.0
    for j in cols[n_skew:n_skew + n_bin]:         # binary (sex, comorbidity flags)
        X[:, j] = (X[:, j] > 0).astype(float)
    sd = X.std(0); sd[sd == 0] = 1.0
    return (X - X.mean(0)) / sd


def _pattern_sizes(rng, n, n_patterns, concentration):
    """Row counts per pattern under a Zipf-like law.

    ``concentration`` in [0, 1]: 1.0 -> a few dominant, well-supported patterns
    (hypothyroid-like); 0.0 -> many near-unique patterns (colic-like).
    """
    a = 0.2 + 2.3 * float(np.clip(concentration, 0.0, 1.0))
    w = 1.0 / np.power(np.arange(1, n_patterns + 1), a)
    w = w / w.sum()
    counts = rng.multinomial(n, w)
    return counts


def _sample_masks(rng, d, blocks, n_patterns, p):
    """``n_patterns`` distinct block-masks, each block hidden with probability ``p``."""
    masks, seen = [], set()
    for _ in range(n_patterns * 50):
        if len(masks) >= n_patterns:
            break
        hide = rng.random(len(blocks)) < p
        if hide.all():
            hide[rng.integers(len(blocks))] = False       # never hide everything
        m = np.ones(d, dtype=bool)                        # True = observed
        for bi, blk in enumerate(blocks):
            if hide[bi]:
                m[blk] = False
        key = m.tobytes()
        if key in seen:
            continue
        seen.add(key)
        masks.append(m)
    while len(masks) < n_patterns:                        # exhausted distinct masks
        masks.append(masks[rng.integers(len(masks))].copy())
    return masks


def _pattern_masks(rng, d, n_patterns, n_blocks, sizes, target_miss=0.12):
    """Distinct masks paired with pattern sizes so the realised missing rate matches.

    ``n_blocks`` controls the granularity of the missingness: few blocks =
    instrument/panel/schema-level dropout (a handful of distinct patterns, as in
    hypothyroid or a multi-site merge); ``n_blocks == d`` = per-feature dropout
    (thousands of near-unique patterns, as in support2/colic). Since at most
    ``2**n_blocks - 1`` distinct masks exist, ``n_blocks`` is raised automatically
    when many patterns are requested -- otherwise the requested count collapses.

    Two corrections are needed to hit the target missing rate. First, requiring
    masks to be DISTINCT biases the accepted set towards heavier masks: at a low
    hide probability most draws hide nothing, only one such mask can be kept, and
    every later acceptance must therefore hide more. Second, the largest patterns
    are matched to the LEAST-hidden masks, which both counteracts that bias and is
    what real data looks like -- the dominant pattern is typically the complete or
    near-complete one. The per-block hide probability is then calibrated by
    bisection on the SUPPORT-WEIGHTED missing rate, which is the quantity that is
    actually observed, rather than on the per-mask rate.
    """
    # Enough blocks that the requested number of DISTINCT masks can be formed while
    # each still hides only about ``target_miss`` of them. With too few blocks the
    # only way to make many distinct masks is to hide more of each, which puts a
    # floor on the missing rate above the target (e.g. 35 masks from 7 blocks needs
    # 2-3 hidden blocks apiece, i.e. >=0.29 missing whatever the target says).
    from math import comb
    nb = max(int(n_blocks), 1)
    while nb < d:
        k = max(1, int(round(target_miss * nb)))
        if sum(comb(nb, j) for j in range(k + 1)) >= n_patterns:
            break
        nb += 1
    n_blocks = int(np.clip(nb, 1, d))
    blocks = np.array_split(np.arange(d), n_blocks)
    sizes = np.sort(np.asarray(sizes))[::-1]              # descending support
    total = max(int(sizes.sum()), 1)

    def realised(masks):
        order = np.argsort([int((~m).sum()) for m in masks])   # least hidden first
        ordered = [masks[i] for i in order]
        hidden = np.array([int((~m).sum()) for m in ordered], dtype=float)
        return float((sizes * hidden).sum() / (total * d)), ordered

    lo, hi, best = 1e-4, 0.95, None
    for _ in range(24):
        p = 0.5 * (lo + hi)
        rate, ordered = realised(_sample_masks(rng, d, blocks, n_patterns, p))
        best = ordered
        if rate > target_miss:
            hi = p
        else:
            lo = p
        if abs(rate - target_miss) < 0.005:
            break
    return best, sizes


def make_dataset(
    n=4000, d=16, n_patterns=6, n_blocks=4, concentration=1.0,
    mechanism="MAR", het=1.0, info=1.0, prevalence=None, target_miss=0.12, seed=0,
    outcome_from="pattern",
):
    """Generate (X_with_nan, y, meta).

    mechanism: 'MCAR' | 'MAR' | 'MNAR' (see module docstring).
    het/info : slope heterogeneity / base-rate informativeness across patterns.
    prevalence: target positive rate (e.g. 0.08 for a clinical cohort); None keeps
                the natural rate implied by the linear predictor.
    outcome_from: 'pattern' draws the outcome from each row's OWN pattern coefficients,
                which is the standard way to simulate pattern heterogeneity and which makes
                coefficient divergence predictive by construction. 'shared' draws it from the
                shared vector beta0 instead, so patterns still differ in their coefficients and
                in their populations but not in the conditional relationship between X and y.
                The second is the control the oracle-bound paper proposes in its Section on
                simulation practice and records as not having run.
    """
    rng = np.random.default_rng(seed)
    X = _latent_features(rng, n, d)
    sizes = _pattern_sizes(rng, n, n_patterns, concentration)
    # masks come back ordered least-hidden first, paired with sizes descending
    masks, sizes = _pattern_masks(rng, d, n_patterns, n_blocks, sizes,
                                  target_miss=target_miss)

    # --- assign rows to patterns (ampute-style weighted-sum scores) ---
    if mechanism == "MCAR":
        scores = rng.normal(size=(n, n_patterns))
    else:
        scores = np.empty((n, n_patterns))
        for k, m in enumerate(masks):
            # MAR  -> driven by variables the pattern KEEPS observed
            # MNAR -> driven by the variables the pattern HIDES
            src = m if mechanism == "MAR" else ~m
            if not src.any():
                src = np.ones(d, dtype=bool)
            w = rng.normal(size=int(src.sum()))
            scores[:, k] = X[:, src] @ w
        scores = (scores - scores.mean(0)) / (scores.std(0) + 1e-9)
        scores = scores + rng.gumbel(size=(n, n_patterns))   # stochastic assignment
    # respect the target pattern-size law: highest scorers claim the larger patterns
    order = np.argsort(-sizes)
    assign = np.full(n, -1)
    free = np.ones(n, dtype=bool)
    for k in order:
        need = int(sizes[k])
        if need <= 0:
            continue
        cand = np.flatnonzero(free)
        if cand.size == 0:
            break
        take = cand[np.argsort(-scores[cand, k])[:need]]
        assign[take] = k
        free[take] = False
    assign[assign < 0] = rng.integers(0, n_patterns, int((assign < 0).sum()))

    # --- outcome: shared effect + pattern-specific slopes/intercept ---
    beta0 = rng.normal(0, 1.0, d)
    betas = {k: beta0 + het * rng.normal(0, 1.0, d) for k in range(n_patterns)}
    inters = {k: info * rng.normal(0, 1.0) for k in range(n_patterns)}
    if outcome_from == "shared":
        lin = np.array([inters[assign[i]] + X[i] @ beta0 for i in range(n)])
    elif outcome_from == "pattern":
        lin = np.array([inters[assign[i]] + X[i] @ betas[assign[i]] for i in range(n)])
    else:
        raise ValueError(f"outcome_from must be 'pattern' or 'shared', got {outcome_from!r}")
    if prevalence is not None:                     # shift intercept to hit the rate
        lo, hi = -20.0, 20.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if expit(lin + mid).mean() > prevalence:
                hi = mid
            else:
                lo = mid
        lin = lin + 0.5 * (lo + hi)
    y = (rng.random(n) < expit(lin)).astype(int)

    Xm = X.copy()
    for i in range(n):
        Xm[i, ~masks[assign[i]]] = np.nan
    # the realised coefficient spread is recorded either way, so the control can be shown to
    # carry the SAME coefficient heterogeneity as the standard generator while its outcome does not
    bmat = np.array([betas[k] for k in range(n_patterns)])
    meta = dict(mechanism=mechanism, het=het, info=info, concentration=concentration,
                n_patterns=n_patterns, assign=assign, prevalence=float(y.mean()),
                outcome_from=outcome_from,
                coef_spread=float(np.mean(np.std(bmat, axis=0))))
    return Xm, y, meta


def dataset_stats(X, y=None):
    """Descriptive statistics matching those measured on the real datasets."""
    pats = [tuple(np.flatnonzero(~np.isnan(r)).tolist()) for r in X]
    c = Counter(pats)
    n = len(pats)
    sizes = np.array(sorted(c.values(), reverse=True))
    p = sizes / n
    out = dict(
        n=n, d=X.shape[1], miss=float(np.isnan(X).mean()),
        n_pat=len(c), pat_per_row=len(c) / n,
        top5=float(sizes[:5].sum() / n),
        cov30=float(sizes[sizes >= 30].sum() / n),
        eff_pat=float(np.exp(-(p * np.log(p)).sum())),
        max_sup=int(sizes[0]),
    )
    if y is not None:
        out["prev"] = float(np.mean(y))
    return out


# Measured on 10 real tabular datasets with native missingness (see paper):
# the range any realistic generator should be able to cover.
REAL_RANGE = {
    "pat_per_row": (0.007, 0.611),   # hypothyroid ... colic
    "cov30": (0.00, 0.98),           # colic ... hypothyroid
    "eff_pat": (1.6, 451.0),         # eucalyptus ... support2
    "miss": (0.03, 0.21),
    "prev": (0.026, 0.55),
}


def in_real_range(stats):
    """Which measured statistics fall inside the observed real-data range."""
    return {k: (lo <= stats[k] <= hi) for k, (lo, hi) in REAL_RANGE.items() if k in stats}
