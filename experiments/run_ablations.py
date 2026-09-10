"""Ablations, including the random-grouping falsification control.

The method: one logistic model per realised missingness pattern, shrunk
toward its immediate ancestors (patterns observing fewer variables, hence
better supported); prediction combines every pattern contained in a row's
observed set, weighted by support. This script ablates that recipe along
several axes and, most importantly, runs the control that can end the paper.

Ablations covered:
    min_support   sweep the support threshold below which a pattern does not
                  get its own submodel ([10, 30, 100, 300]). Tests whether the
                  main-table result is an artefact of one particular
                  threshold choice.
    random_grouping
                  THE FALSIFICATION TEST (``RandomGrouping`` below). Replaces
                  the real missingness-pattern hyperedges with random variable
                  groups matched in count and size, holding everything else
                  fixed -- the per-group logistic models, the cover rule, the
                  support weighting, the shrinkage. If performance does not
                  drop relative to the reference arm, the missingness
                  structure is not doing the work and the paper's central
                  claim is dead. Run across several independent group-draw
                  seeds (not just one) so the falsification verdict does not
                  hinge on a single arbitrary random draw.
    reference     the real patterns at the same pre-specified kappa used
                  everywhere else in this project (see ``_median_support_kappa``
                  below) -- the number every other arm is compared against.

The falsification verdict (Task 16 fixes):
  - ``reference`` and ``random_grouping`` write PER-(seed, fold) rows to
    ``results/ablation_folds.csv`` (in addition to the aggregated
    ``ablations.csv``, unchanged), because every arm shares the exact same
    ``StratifiedKFold`` splits (``run_cv`` derives them from ``seed``/
    ``n_splits`` alone, given identical ``X``/``y``) -- so a PAIRED
    comparison is possible and is what ``report_falsification`` now runs:
    reference vs. random_grouping (the latter reduced to one score per
    (seed, fold) by averaging its three independent group-draw seeds first)
    via a paired Wilcoxon signed-rank test, with a seeded percentile
    bootstrap 95% CI on the median paired drop. The verdict string
    (FALSIFICATION / MARGINAL / SURVIVES) is a summary of that test, not a
    substitute for it -- see ``report_falsification`` and the
    ``MATCH_RATIO_THRESHOLD`` / ``MATERIAL_DROP_THRESHOLD`` constants below
    for the exact, documented boundaries.
  - ``ablations.csv`` gains a ``mean_no_match_rate`` column for every arm
    that tracks it (currently ``reference`` and ``random_grouping``): the
    mean, across CV folds, of the fraction of test rows with no covering
    pattern/group (``HypergraphShrinkage.no_match_rate``, set as a side
    effect of ``predict_proba``), which fall back to the marginal prior.
    This separates "the random arm loses AUPRC because its local models are
    worse" from "the random arm loses AUPRC because more of its test rows
    have no covering group at all" -- two different explanations for the
    same number. Old rows without this column read back as NaN (handled by
    ``_upsert_csv``'s reindex), not a crash.
  - ``report_falsification`` REFUSES to emit a SURVIVES/FALSIFICATION/
    MARGINAL verdict for a cohort whose random control was not actually
    matched in count to the real patterns (mean ``match_ratio`` from
    ``ablation_matchedness.csv`` below ``MATCH_RATIO_THRESHOLD``) -- it
    emits ``UNMATCHED_CONTROL_INVALID`` with the observed ratio instead. A
    performance comparison against an unmatched control does not test the
    hypothesis it claims to (see ``matched_random_groups``'s docstring on
    why small-n runs, including ``--smoke``, undercount badly).

Corrections to the Task 16 brief (which predates data profiling and, in the
draft ``RandomGrouping.fit``, predates a scaler bug -- see below):
  - ``load_cohort`` takes ``feature_set="baseline"`` (default, PRIMARY) or
    ``"full"``. It is a CLI flag here (``--feature-set``), matching
    ``run_h1_h4.py``.
  - Cohorts are subsampled to MAX_N=40,000, stratified and seeded IDENTICALLY
    across every arm -- ``_subsample`` below is copied verbatim from
    ``run_h1_h4.py`` for exactly that reason: the whole point of an ablation
    suite is that every arm sees the same rows.
  - kappa is NEVER hardcoded to 10. Real median pattern support is ~2,000, so
    kappa=10 gives median lambda ~0.995 -- effectively no shrinkage (this
    defect cost a 5.6h run on Task 15; see that task's post-mortem in
    ``run_h1_h4.py``'s module docstring). Every arm here uses the same
    pre-specified operating point as ``run_h1_h4.py``: kappa = median(|S(e)|)
    over the fitted patterns, derived from the TRAINING split inside each CV
    fold, which puts median lambda at exactly 0.5. ``_median_support_kappa``
    below mirrors ``run_h1_h4._median_support_kappa`` -- same rule, kept as a
    local copy rather than a cross-script import since ``experiments/`` is a
    directory of standalone scripts, not a package.
  - Batch support computation uses ``patterns.supports_for`` throughout
    (never a per-pattern Python loop) -- real cohorts realise thousands of
    patterns, and a per-pattern loop over ``support()`` does not finish in
    reasonable time at that scale.
  - The brief's ``RandomGrouping.fit`` never fits ``self.scaler_`` and calls
    ``self._fit_one`` on unscaled ``X``, yet ``HypergraphShrinkage.predict_proba``
    (inherited, not overridden) calls ``self.scaler_.transform(X)`` -- this
    would raise ``AttributeError`` on the very first prediction. Fixed here:
    ``RandomGrouping.fit`` fits its own ``StandardScaler`` on ``X`` (identical
    to ``HypergraphShrinkage.fit``) and fits per-group models on the scaled
    matrix, so a shared variable's coefficient is in the same units whether
    it is estimated inside a real pattern or a random group.

Robustness, mirroring ``run_h1_h4.py`` (the reference for this project):
  - Results are written incrementally, one unit (cohort, ablation, value) at
    a time, never accumulated in memory and flushed at the end.
  - Each unit is wrapped in try/except: a failure is logged and recorded to
    ``results/ablation_failures.csv``, and the run continues.
  - Progress is logged with timestamps and per-unit elapsed time.
  - The run is resumable: a unit already present in its output CSV is
    skipped unless ``--force``. ``_upsert_csv`` (copied from ``run_h1_h4.py``)
    drops only rows matching the FULL key tuple before appending -- an AND of
    per-column equality, not an AND of per-column inequality. The latter is a
    real bug that occurred once already: it deletes a row as soon as ANY
    single column matches, which wipes out every OTHER unit's rows too
    whenever a shared column (e.g. ``cohort``) happens to match.
  - ``--smoke`` runs a drastically reduced configuration (one cohort, one
    seed, two folds, a two-point min_support grid, two random-grouping
    seeds) so the whole pipeline -- including the matched-ness diagnostic and
    resumability -- is verified end to end in well under a minute before any
    cluster run is launched.
  - ``PLCO_ROOT`` overrides the default data path, matching ``run_h1_h4.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from hgmiss import estimator
from hgmiss.data.plco import COHORTS, FEATURE_SETS, load_cohort
from hgmiss.estimator import HypergraphShrinkage
from hgmiss.patterns import extract_patterns, immediate_ancestors, supports_for
from hgmiss.protocol import run_cv
from hgmiss.shrinkage import shrink

ROOT = Path(os.environ.get("PLCO_ROOT",
                           "/Users/tong/Works/tong/phd/datasets/plco"))

# Full-strength configuration.
FULL_SEEDS = list(range(5))
FULL_N_SPLITS = 5
FULL_MAX_N = 40_000
MIN_SUPPORT_GRID = [10, 30, 100, 300]
# Independent random-group draws -- the falsification verdict must not rest
# on one arbitrary draw. Cheap: each seed is one more CV arm, not a new axis
# of model complexity.
RANDOM_GROUP_SEEDS = [0, 1, 2]
# The label-permutation control (Task 16's replacement for random_grouping):
# same real patterns/coverage/kappa, training labels permuted. Several
# independent permutation-draw seeds for the same reason as
# RANDOM_GROUP_SEEDS -- the falsification verdict must not hinge on one
# arbitrary shuffle.
LABEL_PERM_SEEDS = [0, 1, 2]

# Drastically reduced configuration for --smoke: exercises every code path
# (min_support sweep, random-grouping control across multiple seeds,
# reference arm, matched-ness diagnostic, incremental writes, resumability)
# at a scale where a bug surfaces in seconds. Restricted to "prostate", the
# smallest cohort.
SMOKE_SEEDS = [0]
SMOKE_N_SPLITS = 2
SMOKE_MAX_N = 1_500
SMOKE_MIN_SUPPORT_GRID = [10, 100]  # spans the real grid's range
SMOKE_RANDOM_GROUP_SEEDS = [0, 1]
SMOKE_LABEL_PERM_SEEDS = [0, 1]
SMOKE_COHORTS = ["prostate"]

# Placeholder for the "value" column on ablations that don't have a natural
# numeric axis (currently just "reference"). Using 0.0 rather than NaN keeps
# the resumability key round-trippable through a CSV write/read cycle --
# NaN != NaN breaks the tuple-membership check in ``_load_done`` once the
# row has been written and reloaded in a later, resumed invocation.
NO_VALUE = 0.0

# --- falsification verdict boundaries (Task 16 fixes) ---------------------
#
# MATCH_RATIO_THRESHOLD: ``matched_random_groups`` uses rejection sampling
# and can fall short of the real-pattern count at small n (see its
# docstring) -- the full-strength run recovers ~99% of the target count
# (measured 98.6%-100%), while a small or misconfigured run (e.g.
# ``--smoke``, or a partial cohort) can fall to single-digit percentages
# (~6% measured at --smoke scale: 15/236 groups). Below 0.9 the "matched in
# count and size" premise the control depends on no longer holds closely
# enough to trust a comparison against it, so ``report_falsification``
# withholds the verdict (``UNMATCHED_CONTROL_INVALID``) rather than risk
# reporting FALSIFICATION/SURVIVES as if it were a clean test.
MATCH_RATIO_THRESHOLD = 0.9

# MATERIAL_DROP_THRESHOLD: once the paired drop's 95% CI is already known to
# sit reliably above zero, this is the smallest median drop treated as
# practically meaningful rather than a technically-significant sliver.
# Matches the magnitude of the original (unpaired, pre-Task-16) verdict's
# cutoff -- chosen as noticeably larger than typical fold-to-fold AUPRC
# noise on these cohorts, not tuned to any particular run's result.
MATERIAL_DROP_THRESHOLD = 0.01

# Percentile bootstrap over the paired per-(seed, fold) differences, for a
# 95% CI on the median drop. Seeded so the falsification report is
# reproducible across re-runs against the same ablation_folds.csv.
BOOTSTRAP_SEED = 0
N_BOOTSTRAP = 10_000

# NO_MATCH_PARITY_TOLERANCE: the label-permutation control is coverage-matched
# BY CONSTRUCTION (it runs the exact reference patterns/coverage, only the
# training labels are shuffled), so its no-match rate should equal the
# reference's up to fold-to-fold noise. This is the analogue, for that
# control, of MATCH_RATIO_THRESHOLD for random_grouping: if the two no-match
# rates differ by more than this, something is wrong with the claim that the
# control is coverage-matched, and ``report_falsification_permutation``
# flags it in the verdict (there is no separate withheld-verdict state here,
# unlike random_grouping's UNMATCHED_CONTROL_INVALID, because a parity
# violation would indicate a bug in this script rather than an expected
# small-n effect).
NO_MATCH_PARITY_TOLERANCE = 0.02


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def _subsample(c, seed: int = 0, max_n: int = FULL_MAX_N):
    """Stratified subsample to ``max_n``, identical rows for every arm.

    Copied verbatim from ``run_h1_h4.py``'s ``_subsample`` -- the whole point
    of an ablation suite is that every arm sees exactly the same rows, so
    this must not drift from the reference script's mechanism.
    """
    if c.X.shape[0] <= max_n:
        return c.X, c.y
    idx = np.arange(c.X.shape[0])
    keep, _ = train_test_split(
        idx, train_size=max_n, stratify=c.y, random_state=seed
    )
    return c.X[keep], c.y[keep]


def _median_support_kappa(recorded: list[float]):
    """Callable ``kappa(supports) -> float``: the pre-specified operating point.

    Mirrors ``run_h1_h4.py``'s ``_median_support_kappa`` exactly -- kappa =
    median(|S(e)|) over the fitted patterns puts median lambda = |S(e)| /
    (|S(e)| + kappa) at exactly 0.5, and it is derived from the TRAINING
    fold's supports alone (never the held-out rows), so no optimism
    correction is needed. Kept as a local copy rather than importing across
    sibling scripts, since ``experiments/`` has no package ``__init__.py``.
    """
    def _kappa(supports: dict) -> float:
        k = float(np.median(list(supports.values())))
        recorded.append(k)
        return k
    return _kappa


def matched_random_groups(
    mask: np.ndarray,
    real_patterns: list[frozenset[int]],
    min_support: int,
    seed: int,
    max_rounds: int = 20,
    batch_multiplier: int = 6,
    min_batch: int = 20,
) -> tuple[list[frozenset[int]], dict[int, int]]:
    """Random variable groups matched in count and size to ``real_patterns``.

    ``real_patterns`` should be the FULL set of realised patterns (before the
    ``min_support`` filter) -- this function applies the filter itself, to
    exactly the same threshold the caller will later apply to the random
    groups' own supports.

    THE BRIEF'S DRAFT DREW ONE CANDIDATE PER TARGET SIZE AND KEPT WHATEVER
    SURVIVED THE min_support FILTER. Measured on real PLCO data that
    undercounts badly: at n=40,000, prostate/baseline realises 3,365
    qualifying patterns (mean size ~77 of 91 variables) but the one-shot
    draw yields only ~300-400 surviving random groups (~10%). The reason is
    structural, not a coding bug: real missingness patterns are coherent
    blocks (a whole questionnaire section skipped together), so their
    support -- P(all pattern variables observed in a row) -- stays high even
    for large patterns. A RANDOM subset of the same size draws variables
    with uncorrelated (or weakly correlated) missingness, so the probability
    that ALL of them are simultaneously observed collapses combinatorially
    with size. Most one-shot random draws of size ~77 fall below
    min_support and are silently dropped, so "matched count" was violated by
    roughly an order of magnitude -- exactly the failure mode the brief's
    own Step 2 sanity check exists to catch.

    FIX: rejection sampling. For each target size, draw batches of candidate
    subsets and keep testing until enough of them clear min_support (up to
    ``max_rounds`` batches of ``max(count_needed * batch_multiplier,
    min_batch)`` candidates each), so the accepted count tracks the number
    of real patterns at that size rather than whatever a single lucky draw
    produces. Measured on real PLCO data: n=40,000 recovers 3,317/3,365
    (98.6%) of the target count at matched mean size (77.12 vs 77.26);
    the full cohort (n=76,661) recovers all 5,266 exactly (mean size
    matches to 2dp in both cases). A residual
    shortfall is possible and reported (not hidden) via the returned dict --
    for sizes near ``d`` there may be too few distinct size-``s`` subsets in
    total (or too few that clear min_support) to fully match; this is a hard
    combinatorial ceiling, not a bug.

    Batches support computation via ``supports_for`` for every candidate
    batch -- real cohorts realise thousands of patterns, and a per-candidate
    Python-loop call to ``support()`` does not finish in reasonable time at
    that scale.

    Returns ``(groups, shortfall)``: ``groups`` is the (unfit) pattern list
    -- no model is fitted here, which is what makes the matched-ness sanity
    check in ``do_matchedness`` cheap: it inspects pattern/ancestor
    STRUCTURE without ever fitting a logistic model, unlike the actual
    ablation arm (``RandomGrouping.fit``, which calls this function and then
    fits per-group models on the result). ``shortfall`` maps a target size to
    how many groups of that size could not be found within the round/batch
    budget (empty when every size was matched).
    """
    real_supports = supports_for(real_patterns, mask)
    size_counts: dict[int, int] = {}
    for e in real_patterns:
        if real_supports[e] >= min_support:
            s = len(e)
            size_counts[s] = size_counts.get(s, 0) + 1
    if not size_counts:
        return [], {}

    rng = np.random.default_rng(seed)
    d = mask.shape[1]
    accepted: set[frozenset[int]] = set()
    shortfall: dict[int, int] = {}

    for s, count_needed in size_counts.items():
        s = min(s, d)
        found: set[frozenset[int]] = set()
        rounds_left = max_rounds
        while len(found) < count_needed and rounds_left > 0:
            rounds_left -= 1
            batch_n = max(count_needed * batch_multiplier, min_batch)
            candidates: list[frozenset[int]] = []
            seen_this_batch: set[frozenset[int]] = set()
            # Bounded dedup loop -- for s close to d there are few distinct
            # size-s subsets in total, so this can exhaust attempts without
            # filling the batch; that is fine, the batch is just smaller.
            tries = 0
            while len(candidates) < batch_n and tries < batch_n * 20:
                tries += 1
                cand = frozenset(rng.choice(d, size=s, replace=False).tolist())
                if cand in accepted or cand in found or cand in seen_this_batch:
                    continue
                seen_this_batch.add(cand)
                candidates.append(cand)
            if not candidates:
                break  # exhausted the distinct size-s subset space
            batch_supports = supports_for(candidates, mask)
            for cand in candidates:
                if len(found) >= count_needed:
                    break
                if batch_supports[cand] >= min_support:
                    found.add(cand)
        accepted |= found
        if len(found) < count_needed:
            shortfall[s] = count_needed - len(found)

    return list(accepted), shortfall


class RandomGrouping(HypergraphShrinkage):
    """The random-grouping control: same number and sizes of hyperedges, but
    variables chosen at random instead of realised missingness patterns.

    Everything else is held fixed -- the per-group logistic models, the cover
    rule, the support weighting, the shrinkage -- so a performance drop is
    attributable to the missingness structure, not to some other change in
    the recipe.

    KNOWN CONFOUND, stated here and in the paper: random subsets rarely nest,
    so the random groups have almost no containment order and shrinkage has
    little to act on. This control therefore varies "realised missingness
    structure" together with "a hierarchy exists at all" -- it is not a clean
    single-factor ablation. It still answers the question that matters --
    does the actual missingness grouping beat an arbitrary one of matched
    size and count -- but reporting it as a clean ablation would overclaim.
    The kappa path (H1, in ``run_h1_h4.py``) separates the shrinkage
    contribution; ``do_matchedness`` below quantifies this confound directly
    by reporting, per cohort, how many real versus random groups have at
    least one ancestor.
    """

    def __init__(self, kappa: float = 10.0, min_support: int = 30, seed: int = 0):
        super().__init__(kappa, min_support)
        self.seed = seed

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomGrouping":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y).ravel()
        self.prior_ = float(y.mean())
        self.n_features_ = X.shape[1]

        # Fit our own scaler -- HypergraphShrinkage.predict_proba (inherited,
        # not overridden) calls self.scaler_.transform(X), so this cannot be
        # skipped. See the module docstring: the brief's draft omitted this
        # and would raise AttributeError on the first prediction.
        self.scaler_ = StandardScaler().fit(X)
        X_scaled = self.scaler_.transform(X)

        mask = ~np.isnan(X)
        real = [e for e in extract_patterns(mask) if e]
        groups, shortfall = matched_random_groups(mask, real, self.min_support, self.seed)
        self.matched_shortfall_ = shortfall
        if not groups:
            self.raw_theta_, self.theta_, self.ancestors_ = {}, {}, {}
            self.patterns_, self.supports_ = [], {}
            return self

        self.supports_ = supports_for(groups, mask)
        self.patterns_ = [
            g for g in groups if self.supports_[g] >= self.min_support
        ]
        if not self.patterns_:
            self.raw_theta_, self.theta_, self.ancestors_ = {}, {}, {}
            return self

        self.ancestors_ = immediate_ancestors(self.patterns_)
        self.raw_theta_ = {
            g: self._fit_one(X_scaled, y, mask, g) for g in self.patterns_
        }
        self.theta_ = shrink(
            self.raw_theta_, self.supports_, self.ancestors_, self.kappa
        )
        return self


def random_group_fp(
    group_seed: int, kappa, min_support: int = 30,
    no_match_rates: list[float] | None = None,
):
    """``protocol.FitPredict`` adapter for ``RandomGrouping``.

    ``kappa`` is either a fixed float or a callable ``kappa(supports) ->
    float`` (see ``_median_support_kappa``) -- the same two-phase pattern as
    ``estimator.fit_predict`` / ``baselines.pattern.spsm_global``: fit once
    with a kappa=0.0 placeholder to obtain ``raw_theta_``/``supports_``/
    ``ancestors_`` (which do not depend on kappa at all), derive the real
    kappa from THIS fold's fitted-pattern supports, then re-run only the
    cheap shrink step at the derived value.

    If ``no_match_rates`` is given, each fold's ``est.no_match_rate`` --
    the fraction of test rows with no covering random group, which fall back
    to the marginal prior (Finding 2: an alternative explanation for AUPRC
    loss distinct from "the local models are worse") -- is appended to it,
    as a side effect of the SAME ``predict_proba`` call whose output is
    returned, so it always reflects exactly the predictions being scored. In
    the degenerate case where no groups survive ``min_support`` at all,
    every row necessarily falls back, so the rate is recorded as 1.0 without
    a ``predict_proba`` call (there is nothing to predict with).
    """
    def _fp(X_tr, y_tr, X_te):
        est = RandomGrouping(kappa=0.0, min_support=min_support, seed=group_seed)
        est.fit(X_tr, y_tr)
        if not est.raw_theta_:
            if no_match_rates is not None:
                no_match_rates.append(1.0)
            return np.full(len(X_te), est.prior_)
        if callable(kappa):
            fitted_supports = {e: est.supports_[e] for e in est.patterns_}
            k = kappa(fitted_supports)
        else:
            k = kappa
        est.kappa = k
        est.theta_ = shrink(est.raw_theta_, est.supports_, est.ancestors_, k)
        proba = est.predict_proba(X_te)
        if no_match_rates is not None:
            no_match_rates.append(est.no_match_rate)
        return proba
    return _fp


def reference_fp(
    kappa, min_support: int = 30, no_match_rates: list[float] | None = None,
):
    """``protocol.FitPredict`` adapter for the reference arm (real patterns).

    Duplicates ``estimator.fit_predict``'s callable-kappa two-phase fit
    (fit once at kappa=0.0 for ``raw_theta_``/``supports_``/``ancestors_``,
    derive kappa from the TRAINING fold's supports alone, then re-run only
    the shrink step) -- kept as a local copy rather than calling
    ``estimator.fit_predict`` directly, because that adapter returns only
    probabilities and hides the fitted ``HypergraphShrinkage`` object, and
    Finding 2 needs ``est.no_match_rate`` off of it. Not folded into
    ``estimator.fit_predict`` itself since ``run_h1_h4.py`` also depends on
    that exact signature and must not be touched by this ablation script.
    See ``random_group_fp`` above for the matching ``no_match_rates``
    contract (appended as a side effect of the returned ``predict_proba``
    call; degenerate no-patterns-fitted case recorded as rate 1.0).
    """
    def _fp(X_tr, y_tr, X_te):
        est = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(X_tr, y_tr)
        if not est.raw_theta_:
            if no_match_rates is not None:
                no_match_rates.append(1.0)
            return np.full(len(X_te), est.prior_)
        if callable(kappa):
            fitted_supports = {e: est.supports_[e] for e in est.patterns_}
            k = kappa(fitted_supports)
        else:
            k = kappa
        est.kappa = k
        est.theta_ = shrink(est.raw_theta_, est.supports_, est.ancestors_, k)
        proba = est.predict_proba(X_te)
        if no_match_rates is not None:
            no_match_rates.append(est.no_match_rate)
        return proba
    return _fp


def permuted_label_fp(
    perm_seed: int, kappa, min_support: int = 30,
    no_match_rates: list[float] | None = None,
):
    """``protocol.FitPredict`` adapter for the label-permutation control.

    THE REPLACEMENT FOR ``random_group_fp``. Runs the EXACT reference recipe
    -- real patterns, real coverage, the same per-fold ``kappa =
    median(|S(e)|)`` operating point -- but fits on a PERMUTED copy of the
    training labels: ``y_perm = np.random.default_rng(perm_seed).permutation(
    y_tr)``. The permutation preserves class balance (same count of
    positives) while destroying the association between ``X`` and ``y``, so
    any AUPRC/AUROC this arm achieves above chance would have to come from
    the ensemble machinery itself (the cover rule, the support weighting,
    the shrinkage) rather than genuine pattern-conditional signal.

    Because the patterns, their supports, and the coverage of test rows are
    identical to the reference arm's (only the fitted coefficients differ,
    since the labels used to fit them are shuffled), this control's
    ``no_match_rate`` matches the reference's -- unlike ``random_group_fp``,
    whose random groups rarely cover a test row at all (measured no-match
    rate 0.97 against the reference's ~0) and are, on high-d/high-missingness
    cohorts, not even constructible in matched count (see
    ``matched_random_groups``'s docstring). That no-match parity is the
    whole point: it is what makes this a genuinely coverage-matched control,
    which is what makes a performance gap between it and the reference
    attributable to the missingness structure being informative, not to a
    difference in how often either arm can predict at all.

    Only ``y_tr`` is ever touched -- ``X_tr`` and ``X_te`` are passed through
    unmodified, exactly as in ``reference_fp``. This mirrors ``reference_fp``
    and ``random_group_fp``'s two-phase callable-kappa handling (fit once at
    kappa=0.0 for ``raw_theta_``/``supports_``/``ancestors_``, derive kappa
    from the TRAINING fold's fitted-pattern supports alone, then re-run only
    the cheap shrink step) and their ``no_match_rates`` side-effect contract
    (appended once per call, as a side effect of the SAME ``predict_proba``
    call whose output is returned; the degenerate no-patterns-fitted case is
    recorded as rate 1.0 without a ``predict_proba`` call).
    """
    def _fp(X_tr, y_tr, X_te):
        rng = np.random.default_rng(perm_seed)
        y_perm = rng.permutation(np.asarray(y_tr).ravel())
        est = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(X_tr, y_perm)
        if not est.raw_theta_:
            if no_match_rates is not None:
                no_match_rates.append(1.0)
            return np.full(len(X_te), est.prior_)
        if callable(kappa):
            fitted_supports = {e: est.supports_[e] for e in est.patterns_}
            k = kappa(fitted_supports)
        else:
            k = kappa
        est.kappa = k
        est.theta_ = shrink(est.raw_theta_, est.supports_, est.ancestors_, k)
        proba = est.predict_proba(X_te)
        if no_match_rates is not None:
            no_match_rates.append(est.no_match_rate)
        return proba
    return _fp


def structure_summary(
    patterns: list[frozenset[int]],
    ancestors: dict[frozenset[int], list[frozenset[int]]],
) -> tuple[int, float, int, float]:
    """``(n_groups, mean_size, n_with_ancestor, frac_with_ancestor)``."""
    n = len(patterns)
    if n == 0:
        return 0, 0.0, 0, 0.0
    mean_size = float(np.mean([len(e) for e in patterns]))
    with_anc = sum(1 for e in patterns if ancestors.get(e))
    return n, mean_size, with_anc, with_anc / n


ABLATION_COLUMNS = [
    "cohort", "ablation", "value", "feature_set", "subsample_n",
    "n_seeds", "n_splits", "auprc", "auprc_sd", "auroc", "auroc_sd",
    # Finding 2: mean, across CV folds, of the fraction of test rows with no
    # covering pattern/group (falls back to the marginal prior). NaN for
    # arms that don't track it (currently everything but reference,
    # random_grouping, and label_permutation) and for rows written before
    # this column existed -- ``_upsert_csv``'s reindex handles the schema
    # upgrade on read.
    "mean_no_match_rate",
]
# Per-(seed, fold) rows for the arms the paired falsification tests need
# (Finding 1, plus the Task 16 label_permutation replacement) -- currently
# reference, random_grouping, and label_permutation. Keyed the
# same as ABLATION_COLUMNS' unit key: all folds for one (cohort, ablation,
# value, feature_set) unit are computed and written together in a single
# ``run_cv`` call, so upserting on that key (dropping any prior rows for the
# unit, then appending the fresh set) is resumable/duplicate-safe exactly
# like ``ablations.csv`` -- a resumed run only reaches the write when the
# unit was NOT already in ``done_ablation``.
FOLD_COLUMNS = ["cohort", "ablation", "value", "feature_set", "seed", "fold", "auprc", "auroc"]
MATCH_COLUMNS = [
    "cohort", "feature_set", "subsample_n", "min_support", "group_seed",
    "real_n_groups", "real_mean_size", "real_n_with_ancestor", "real_frac_with_ancestor",
    "random_n_groups", "random_mean_size", "random_n_with_ancestor", "random_frac_with_ancestor",
    "match_ratio", "rejection_shortfall",
]
FAILURE_COLUMNS = ["timestamp", "stage", "cohort", "unit", "feature_set", "error"]

ABLATION_KEY = ["cohort", "ablation", "value", "feature_set"]
FOLD_KEY = ABLATION_KEY
MATCH_KEY = ["cohort", "feature_set", "min_support", "group_seed"]


def _append_csv(path: Path, df: pd.DataFrame, columns: list[str]) -> None:
    df = df.reindex(columns=columns)
    header = not (path.exists() and path.stat().st_size > 0)
    df.to_csv(path, mode="a", header=header, index=False)


def _upsert_csv(
    path: Path, new_df: pd.DataFrame, columns: list[str],
    key_cols: list[str], key_values: tuple,
) -> None:
    """Write ``new_df`` for this unit, first dropping any existing rows that
    match ``key_values`` on ``key_cols``.

    Copied from ``run_h1_h4.py``'s ``_upsert_csv``. Under normal
    (non-``--force``) operation the caller only reaches here when the key was
    NOT already present, so the drop is a no-op. It matters under
    ``--force``: a plain append would leave both the old and the recomputed
    rows in the file, silently duplicating a unit's rows. ``match`` is True
    only for rows equal to this key on EVERY key column (an AND of
    per-column equality) -- do not build this as an AND of per-column
    ``!=``, which drops a row as soon as ANY single column matches and wipes
    out every OTHER unit's rows too whenever a shared column (e.g.
    ``cohort``) happens to match. That bug already occurred once in this
    project.
    """
    new_df = new_df.reindex(columns=columns)
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path)
        match = pd.Series(True, index=existing.index)
        for col, val in zip(key_cols, key_values):
            match &= existing[col] == val
        existing = existing.loc[~match].reindex(columns=columns)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(path, index=False)


def _load_done(path: Path, key_cols: list[str]) -> set[tuple]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    df = pd.read_csv(path, usecols=key_cols)
    return set(map(tuple, df[key_cols].drop_duplicates().to_numpy().tolist()))


class Runner:
    """Owns the output directory, resumability state, and failure log."""

    def __init__(self, out_dir: Path, force: bool):
        self.out = out_dir
        self.force = force
        self.ablation_path = self.out / "ablations.csv"
        self.folds_path = self.out / "ablation_folds.csv"
        self.match_path = self.out / "ablation_matchedness.csv"
        self.failures_path = self.out / "ablation_failures.csv"

        self.done_ablation = _load_done(self.ablation_path, ABLATION_KEY)
        self.done_match = _load_done(self.match_path, MATCH_KEY)
        self.failures: list[dict] = []

    def record_failure(self, stage: str, cohort: str, unit: str, feature_set: str, exc: Exception) -> None:
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "stage": stage, "cohort": cohort, "unit": unit,
            "feature_set": feature_set, "error": f"{type(exc).__name__}: {exc}",
        }
        self.failures.append(row)
        _append_csv(self.failures_path, pd.DataFrame([row]), FAILURE_COLUMNS)
        log(f"FAILED [{stage}] cohort={cohort} unit={unit} feature_set={feature_set}: "
            f"{type(exc).__name__}: {exc}")
        log(traceback.format_exc())

    def do_ablation(
        self, cohort, ablation, value, fn, X, y, seeds, n_splits, feature_set,
        save_folds: bool = False, no_match_rates: list[float] | None = None,
    ) -> None:
        """Run one (cohort, ablation, value, feature_set) unit.

        ``save_folds``: also persist the per-(seed, fold) rows to
        ``ablation_folds.csv`` (Finding 1) -- needed for reference and
        random_grouping (the paired falsification test), not for the
        min_support sweep. ``no_match_rates``: if given, MUST be the same
        list object passed into ``fn``'s construction (see ``reference_fp``/
        ``random_group_fp``) -- ``fn`` appends to it during ``run_cv`` below,
        and its mean is recorded here as ``mean_no_match_rate`` (Finding 2).
        """
        key = (cohort, ablation, value, feature_set)
        if key in self.done_ablation and not self.force:
            log(f"skip [{ablation}] {cohort}/value={value}/{feature_set} (already present)")
            return
        t0 = time.time()
        try:
            df = run_cv(fn, X, y, seeds=seeds, n_splits=n_splits)
            mean_no_match = float(np.mean(no_match_rates)) if no_match_rates else float("nan")
            row = pd.DataFrame([{
                "cohort": cohort, "ablation": ablation, "value": value,
                "feature_set": feature_set, "subsample_n": X.shape[0],
                "n_seeds": len(seeds), "n_splits": n_splits,
                "auprc": df.auprc.mean(), "auprc_sd": df.auprc.std(),
                "auroc": df.auroc.mean(), "auroc_sd": df.auroc.std(),
                "mean_no_match_rate": mean_no_match,
            }])
            _upsert_csv(self.ablation_path, row, ABLATION_COLUMNS, ABLATION_KEY, key)
            self.done_ablation.add(key)

            if save_folds:
                fold_df = df[["seed", "fold", "auprc", "auroc"]].copy()
                fold_df["cohort"] = cohort
                fold_df["ablation"] = ablation
                fold_df["value"] = value
                fold_df["feature_set"] = feature_set
                _upsert_csv(self.folds_path, fold_df, FOLD_COLUMNS, FOLD_KEY, key)

            elapsed = time.time() - t0
            log(f"done [{ablation}] {cohort}/value={value}/{feature_set} "
                f"({len(seeds)} seeds x {n_splits} folds) auprc={row.auprc.iloc[0]:.4f} "
                f"no_match={mean_no_match:.4f} in {elapsed:.1f}s")
        except Exception as exc:  # noqa: BLE001 -- deliberate: log and continue
            self.record_failure(ablation, cohort, str(value), feature_set, exc)

    def do_matchedness(
        self, cohort, X, y, feature_set, min_support: int, group_seeds: list[int],
    ) -> None:
        """Structure-only sanity check (no logistic models fitted): confirms
        the random control really is matched to the real patterns, and
        quantifies the containment-order confound documented in
        ``RandomGrouping``'s docstring.
        """
        mask = ~np.isnan(X)
        real_all = [e for e in extract_patterns(mask) if e]
        real_supports = supports_for(real_all, mask)
        real_patterns = [e for e in real_all if real_supports[e] >= min_support]
        real_ancestors = immediate_ancestors(real_patterns)
        r_n, r_size, r_with_anc, r_frac = structure_summary(real_patterns, real_ancestors)

        for gs in group_seeds:
            key = (cohort, feature_set, float(min_support), float(gs))
            if key in self.done_match and not self.force:
                log(f"skip [matchedness] {cohort}/min_support={min_support}/seed={gs} "
                    f"(already present)")
                continue
            t0 = time.time()
            try:
                groups, shortfall = matched_random_groups(mask, real_all, min_support, gs)
                rand_supports = supports_for(groups, mask)
                rand_patterns = [g for g in groups if rand_supports[g] >= min_support]
                rand_ancestors = immediate_ancestors(rand_patterns)
                g_n, g_size, g_with_anc, g_frac = structure_summary(rand_patterns, rand_ancestors)
                shortfall_total = sum(shortfall.values())

                row = pd.DataFrame([{
                    "cohort": cohort, "feature_set": feature_set,
                    "subsample_n": X.shape[0], "min_support": float(min_support),
                    "group_seed": float(gs),
                    "real_n_groups": r_n, "real_mean_size": r_size,
                    "real_n_with_ancestor": r_with_anc, "real_frac_with_ancestor": r_frac,
                    "random_n_groups": g_n, "random_mean_size": g_size,
                    "random_n_with_ancestor": g_with_anc, "random_frac_with_ancestor": g_frac,
                    "match_ratio": (g_n / r_n) if r_n else float("nan"),
                    "rejection_shortfall": shortfall_total,
                }])
                _upsert_csv(self.match_path, row, MATCH_COLUMNS, MATCH_KEY, key)
                self.done_match.add(key)
                elapsed = time.time() - t0
                log(f"done [matchedness] {cohort}/min_support={min_support}/seed={gs}: "
                    f"real n={r_n} mean_size={r_size:.2f} frac_anc={r_frac:.3f} | "
                    f"random n={g_n} mean_size={g_size:.2f} frac_anc={g_frac:.3f} "
                    f"match_ratio={(g_n / r_n) if r_n else float('nan'):.3f} "
                    f"rejection_shortfall={shortfall_total} in {elapsed:.1f}s")
            except Exception as exc:  # noqa: BLE001
                self.record_failure(
                    "matchedness", cohort,
                    f"min_support={min_support}/seed={gs}", feature_set, exc,
                )

    def report_falsification(self, feature_set: str) -> None:
        """Step 4 of the brief: PAIRED reference-vs-random_grouping test.

        Recomputed from the per-fold CSV (not from in-memory state) so it is
        correct after a resumed run that skipped some units. Written fresh
        each time -- this is a derived summary, not a source of incremental
        truth, so it does not need resumability bookkeeping of its own.

        Pairing is on (seed, fold): every arm runs ``run_cv`` on identical
        ``X``/``y``/``seeds``/``n_splits``, and ``run_cv`` derives its
        ``StratifiedKFold`` splits purely from ``seed``/``n_splits``, so
        within a (seed, fold) cell the reference and random-grouping scores
        were computed on the exact same held-out rows. The random arm has
        THREE independent group-draw seeds; these are reduced to one score
        per (seed, fold) by averaging across them BEFORE pairing -- the
        honest summary that averages out the arbitrary group draw, which is
        exactly why multiple draws were run in the first place.

        Finding 3 guard: a cohort whose random control was not actually
        matched in count to the real patterns (mean ``match_ratio`` from
        ``ablation_matchedness.csv`` below ``MATCH_RATIO_THRESHOLD``) gets
        ``UNMATCHED_CONTROL_INVALID`` instead of a real verdict -- computing
        a paired test against an unmatched control would answer a different
        question than the one the control is meant to test.
        """
        if not self.folds_path.exists() or self.folds_path.stat().st_size == 0:
            log("no ablation_folds.csv rows yet -- skipping falsification report")
            return
        folds = pd.read_csv(self.folds_path)
        sub = folds[folds.feature_set == feature_set]

        match_df = None
        if self.match_path.exists() and self.match_path.stat().st_size > 0:
            match_df = pd.read_csv(self.match_path)

        ablation_df = None
        if self.ablation_path.exists() and self.ablation_path.stat().st_size > 0:
            ablation_df = pd.read_csv(self.ablation_path)

        rng = np.random.default_rng(BOOTSTRAP_SEED)
        rows = []
        for cohort in sorted(sub.cohort.unique()):
            c = sub[sub.cohort == cohort]
            ref = c[c.ablation == "reference"]
            rnd = c[c.ablation == "random_grouping"]
            if ref.empty or rnd.empty:
                continue

            # Finding 2: surface the mean no-match rate per arm (from the
            # aggregated CSV -- it is a per-unit mean, not a per-fold value)
            # so the report can distinguish "worse local models" from "more
            # test rows fell back to the prior".
            ref_no_match = rnd_no_match = float("nan")
            if ablation_df is not None:
                a = ablation_df[(ablation_df.cohort == cohort) &
                                 (ablation_df.feature_set == feature_set)]
                if "mean_no_match_rate" in a.columns:
                    a_ref = a[a.ablation == "reference"]
                    a_rnd = a[a.ablation == "random_grouping"]
                    if not a_ref.empty:
                        ref_no_match = float(a_ref.mean_no_match_rate.iloc[0])
                    if not a_rnd.empty:
                        rnd_no_match = float(a_rnd.mean_no_match_rate.mean())

            # Finding 3: refuse a verdict on an unmatched control.
            match_ratio_mean = float("nan")
            if match_df is not None:
                m = match_df[(match_df.cohort == cohort) &
                             (match_df.feature_set == feature_set)]
                if not m.empty:
                    match_ratio_mean = float(m.match_ratio.mean())
            if not (np.isfinite(match_ratio_mean) and match_ratio_mean >= MATCH_RATIO_THRESHOLD):
                verdict = (
                    f"UNMATCHED_CONTROL_INVALID: mean match_ratio="
                    f"{match_ratio_mean:.4f} < {MATCH_RATIO_THRESHOLD} -- random "
                    f"control is not matched in count to the real patterns, "
                    f"verdict withheld"
                )
                rows.append({
                    "cohort": cohort, "feature_set": feature_set,
                    "match_ratio_mean": match_ratio_mean,
                    "n_pairs": np.nan, "n_dropped": np.nan,
                    "median_drop": np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
                    "wilcoxon_p": np.nan, "verdict": verdict,
                    "reference_mean_no_match_rate": ref_no_match,
                    "random_grouping_mean_no_match_rate": rnd_no_match,
                })
                log(f"[falsification] {cohort}: {verdict}")
                continue

            # --- pair on (seed, fold) ---
            ref_s = ref.set_index(["seed", "fold"])["auprc"]
            if ref_s.index.duplicated().any():
                raise ValueError(
                    f"duplicate (seed, fold) keys for the reference arm, "
                    f"cohort={cohort} -- fix ablation_folds.csv, do not "
                    f"deduplicate here"
                )
            # Reduce the random arm's 3 independent group-draw seeds to one
            # score per (seed, fold) first (pandas' groupby mean skips NaN,
            # so a single degenerate group-seed fold does not poison the
            # average as long as at least one draw is finite).
            rnd_reduced = rnd.groupby(["seed", "fold"])["auprc"].mean()

            common = ref_s.index.intersection(rnd_reduced.index)
            ref_common = ref_s.loc[common].to_numpy()
            rnd_common = rnd_reduced.loc[common].to_numpy()
            finite = np.isfinite(ref_common) & np.isfinite(rnd_common)
            n_pairs = int(finite.sum())
            n_dropped = int(len(common) - n_pairs)
            diff = ref_common[finite] - rnd_common[finite]

            if n_pairs < 2:
                log(f"[falsification] {cohort}: only {n_pairs} usable paired "
                    f"folds ({n_dropped} dropped as non-finite) -- skipping, "
                    f"cannot run a paired test")
                continue

            median_drop = float(np.median(diff))
            if np.allclose(diff, 0):
                p = 1.0
            else:
                p = float(stats.wilcoxon(diff, zero_method="zsplit").pvalue)

            # Percentile bootstrap 95% CI on the median paired drop.
            boot_idx = rng.integers(0, n_pairs, size=(N_BOOTSTRAP, n_pairs))
            boot_medians = np.median(diff[boot_idx], axis=1)
            ci_lo, ci_hi = (float(v) for v in np.percentile(boot_medians, [2.5, 97.5]))

            # Verdict bands, in terms of the CI on the median paired drop:
            #   FALSIFICATION -- CI touches or crosses zero: reference is
            #     not reliably better than the random control.
            #   SURVIVES -- CI entirely above zero (reliably positive) AND
            #     the median drop clears MATERIAL_DROP_THRESHOLD.
            #   MARGINAL -- CI entirely above zero but the drop is too small
            #     to call practically meaningful.
            if ci_lo <= 0:
                verdict = (
                    f"FALSIFICATION: 95% CI on the paired drop "
                    f"[{ci_lo:.4f}, {ci_hi:.4f}] includes or crosses zero -- "
                    f"reference is not reliably better than random grouping"
                )
            elif median_drop < MATERIAL_DROP_THRESHOLD:
                verdict = (
                    f"MARGINAL: drop reliably positive (CI [{ci_lo:.4f}, "
                    f"{ci_hi:.4f}]) but median {median_drop:.4f} is under "
                    f"{MATERIAL_DROP_THRESHOLD} AUPRC -- structure barely matters"
                )
            else:
                verdict = (
                    f"SURVIVES: reference reliably beats random grouping "
                    f"(median drop {median_drop:.4f}, CI [{ci_lo:.4f}, {ci_hi:.4f}])"
                )

            rows.append({
                "cohort": cohort, "feature_set": feature_set,
                "match_ratio_mean": match_ratio_mean,
                "n_pairs": n_pairs, "n_dropped": n_dropped,
                "median_drop": median_drop, "ci_lo": ci_lo, "ci_hi": ci_hi,
                "wilcoxon_p": p, "verdict": verdict,
                "reference_mean_no_match_rate": ref_no_match,
                "random_grouping_mean_no_match_rate": rnd_no_match,
            })
            log(f"[falsification] {cohort}: median_drop={median_drop:.4f} "
                f"CI=[{ci_lo:.4f},{ci_hi:.4f}] p={p:.4g} n_pairs={n_pairs} "
                f"n_dropped={n_dropped} match_ratio={match_ratio_mean:.4f} "
                f"ref_no_match={ref_no_match:.4f} rnd_no_match={rnd_no_match:.4f} "
                f"-> {verdict}")

        if rows:
            out_path = self.out / f"ablation_falsification_{feature_set}.csv"
            pd.DataFrame(rows).to_csv(out_path, index=False)
            log(f"falsification report written: {out_path}")

    def report_falsification_permutation(self, feature_set: str) -> None:
        """Task 16: PAIRED reference-vs-label_permutation test.

        The replacement falsification test. ADDITIONAL to (not a
        replacement for) ``report_falsification``'s reference-vs-
        random_grouping report above -- that comparison stays, since
        documenting random_grouping's failure (measured no-match rate 0.97,
        AUROC 0.50, unconstructable at high d/high-missingness -- see this
        module's docstring) is itself part of the record.

        Same pairing logic as ``report_falsification``: both arms ran
        ``run_cv`` on identical X/y/seeds/n_splits, so a (seed, fold) cell
        holds identical held-out rows for both. The permutation arm has
        THREE independent perm-seed draws, reduced to one score per (seed,
        fold) by averaging across them before pairing, for the same reason
        as random_grouping's group-draw seeds: the honest summary averages
        out the arbitrary shuffle.

        NO MATCH_RATIO_THRESHOLD guard -- label permutation runs the exact
        reference patterns, so there is no "matched in count" premise to
        fall short of. What CAN fail here is no-match PARITY: this control
        is coverage-matched by construction (real patterns, real coverage --
        only y_tr is permuted), so its no-match rate should equal the
        reference's up to fold noise. A violation beyond
        ``NO_MATCH_PARITY_TOLERANCE`` is flagged directly in the verdict
        string rather than withholding the verdict outright (see
        ``NO_MATCH_PARITY_TOLERANCE``'s definition for why).
        """
        if not self.folds_path.exists() or self.folds_path.stat().st_size == 0:
            log("no ablation_folds.csv rows yet -- skipping permutation falsification report")
            return
        folds = pd.read_csv(self.folds_path)
        sub = folds[folds.feature_set == feature_set]

        ablation_df = None
        if self.ablation_path.exists() and self.ablation_path.stat().st_size > 0:
            ablation_df = pd.read_csv(self.ablation_path)

        rng = np.random.default_rng(BOOTSTRAP_SEED)
        rows = []
        for cohort in sorted(sub.cohort.unique()):
            c = sub[sub.cohort == cohort]
            ref = c[c.ablation == "reference"]
            perm = c[c.ablation == "label_permutation"]
            if ref.empty or perm.empty:
                continue

            ref_no_match = perm_no_match = float("nan")
            if ablation_df is not None:
                a = ablation_df[(ablation_df.cohort == cohort) &
                                 (ablation_df.feature_set == feature_set)]
                if "mean_no_match_rate" in a.columns:
                    a_ref = a[a.ablation == "reference"]
                    a_perm = a[a.ablation == "label_permutation"]
                    if not a_ref.empty:
                        ref_no_match = float(a_ref.mean_no_match_rate.iloc[0])
                    if not a_perm.empty:
                        perm_no_match = float(a_perm.mean_no_match_rate.mean())

            parity_ok = (
                np.isfinite(ref_no_match) and np.isfinite(perm_no_match)
                and abs(ref_no_match - perm_no_match) <= NO_MATCH_PARITY_TOLERANCE
            )
            parity_note = (
                f"no-match parity OK (ref={ref_no_match:.4f}, perm={perm_no_match:.4f})"
                if parity_ok else
                f"NO-MATCH PARITY VIOLATED: ref={ref_no_match:.4f} vs "
                f"perm={perm_no_match:.4f} (tolerance {NO_MATCH_PARITY_TOLERANCE}) "
                f"-- the control is not actually coverage-matched"
            )

            # --- pair on (seed, fold) ---
            ref_s = ref.set_index(["seed", "fold"])["auprc"]
            if ref_s.index.duplicated().any():
                raise ValueError(
                    f"duplicate (seed, fold) keys for the reference arm, "
                    f"cohort={cohort} -- fix ablation_folds.csv, do not "
                    f"deduplicate here"
                )
            perm_reduced = perm.groupby(["seed", "fold"])["auprc"].mean()

            common = ref_s.index.intersection(perm_reduced.index)
            ref_common = ref_s.loc[common].to_numpy()
            perm_common = perm_reduced.loc[common].to_numpy()
            finite = np.isfinite(ref_common) & np.isfinite(perm_common)
            n_pairs = int(finite.sum())
            n_dropped = int(len(common) - n_pairs)
            diff = ref_common[finite] - perm_common[finite]

            if n_pairs < 2:
                verdict = f"INSUFFICIENT_PAIRS: only {n_pairs} usable paired folds. {parity_note}"
                rows.append({
                    "cohort": cohort, "feature_set": feature_set,
                    "n_pairs": n_pairs, "n_dropped": n_dropped,
                    "median_drop": np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
                    "wilcoxon_p": np.nan, "verdict": verdict,
                    "reference_mean_no_match_rate": ref_no_match,
                    "label_permutation_mean_no_match_rate": perm_no_match,
                    "no_match_parity_ok": parity_ok,
                })
                log(f"[falsification/permutation] {cohort}: {verdict}")
                continue

            median_drop = float(np.median(diff))
            if np.allclose(diff, 0):
                p = 1.0
            else:
                p = float(stats.wilcoxon(diff, zero_method="zsplit").pvalue)

            # Percentile bootstrap 95% CI on the median paired drop.
            boot_idx = rng.integers(0, n_pairs, size=(N_BOOTSTRAP, n_pairs))
            boot_medians = np.median(diff[boot_idx], axis=1)
            ci_lo, ci_hi = (float(v) for v in np.percentile(boot_medians, [2.5, 97.5]))

            # Same verdict bands as report_falsification, phrased against
            # label_permutation instead of random_grouping.
            if ci_lo <= 0:
                verdict = (
                    f"FALSIFICATION: 95% CI on the paired drop "
                    f"[{ci_lo:.4f}, {ci_hi:.4f}] includes or crosses zero -- "
                    f"reference is not reliably better than label permutation"
                )
            elif median_drop < MATERIAL_DROP_THRESHOLD:
                verdict = (
                    f"MARGINAL: drop reliably positive (CI [{ci_lo:.4f}, "
                    f"{ci_hi:.4f}]) but median {median_drop:.4f} is under "
                    f"{MATERIAL_DROP_THRESHOLD} AUPRC -- structure barely matters"
                )
            else:
                verdict = (
                    f"SURVIVES: reference reliably beats label permutation "
                    f"(median drop {median_drop:.4f}, CI [{ci_lo:.4f}, {ci_hi:.4f}])"
                )
            verdict = f"{verdict}. {parity_note}"

            rows.append({
                "cohort": cohort, "feature_set": feature_set,
                "n_pairs": n_pairs, "n_dropped": n_dropped,
                "median_drop": median_drop, "ci_lo": ci_lo, "ci_hi": ci_hi,
                "wilcoxon_p": p, "verdict": verdict,
                "reference_mean_no_match_rate": ref_no_match,
                "label_permutation_mean_no_match_rate": perm_no_match,
                "no_match_parity_ok": parity_ok,
            })
            log(f"[falsification/permutation] {cohort}: median_drop={median_drop:.4f} "
                f"CI=[{ci_lo:.4f},{ci_hi:.4f}] p={p:.4g} n_pairs={n_pairs} "
                f"n_dropped={n_dropped} ref_no_match={ref_no_match:.4f} "
                f"perm_no_match={perm_no_match:.4f} -> {verdict}")

        if rows:
            out_path = self.out / f"ablation_falsification_permutation_{feature_set}.csv"
            pd.DataFrame(rows).to_csv(out_path, index=False)
            log(f"permutation falsification report written: {out_path}")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feature-set", choices=FEATURE_SETS, default="baseline",
                    help="baseline (default, PRIMARY analysis) or full (sensitivity)")
    p.add_argument("--force", action="store_true",
                    help="recompute even if an output row already exists")
    p.add_argument("--smoke", action="store_true",
                    help="drastically reduced config for end-to-end verification")
    p.add_argument("--out-dir", default="results", help="output directory")
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.smoke:
        cohorts = SMOKE_COHORTS
        seeds = SMOKE_SEEDS
        n_splits = SMOKE_N_SPLITS
        max_n = SMOKE_MAX_N
        min_support_grid = SMOKE_MIN_SUPPORT_GRID
        group_seeds = SMOKE_RANDOM_GROUP_SEEDS
        perm_seeds = SMOKE_LABEL_PERM_SEEDS
        log(f"SMOKE MODE: cohorts={cohorts} seeds={seeds} n_splits={n_splits} "
            f"max_n={max_n} min_support_grid={min_support_grid} "
            f"random_group_seeds={group_seeds} label_perm_seeds={perm_seeds}")
    else:
        cohorts = sorted(COHORTS)
        seeds = FULL_SEEDS
        n_splits = FULL_N_SPLITS
        max_n = FULL_MAX_N
        min_support_grid = MIN_SUPPORT_GRID
        group_seeds = RANDOM_GROUP_SEEDS
        perm_seeds = LABEL_PERM_SEEDS

    runner = Runner(out, args.force)
    t_start = time.time()

    for cohort in cohorts:
        log(f"=== loading {cohort} (feature_set={args.feature_set}) ===")
        c = load_cohort(cohort, ROOT, feature_set=args.feature_set)
        X, y = _subsample(c, seed=0, max_n=max_n)
        log(f"{cohort}: n={X.shape[0]:,} (of {c.X.shape[0]:,}) d={X.shape[1]} "
            f"prev={y.mean():.2%} feature_set={c.feature_set}")

        # --- A3: min-support threshold sweep ---
        for ms in min_support_grid:
            derived: list[float] = []
            kappa_fn = _median_support_kappa(derived)
            fn = estimator.fit_predict(kappa=kappa_fn, min_support=ms)
            runner.do_ablation(cohort, "min_support", float(ms), fn, X, y,
                                seeds, n_splits, args.feature_set)
            if derived:
                log(f"{cohort}/min_support={ms}: derived kappa median "
                    f"{np.median(derived):.1f} over {len(derived)} folds")

        # --- the random-grouping control, across independent draw seeds ---
        # save_folds=True + no_match_rates: Findings 1 and 2 both need this
        # arm's per-fold scores and no-match rate (paired falsification test
        # and the alternative-explanation check, respectively).
        for gs in group_seeds:
            derived = []
            kappa_fn = _median_support_kappa(derived)
            no_match_rates: list[float] = []
            fn = random_group_fp(group_seed=gs, kappa=kappa_fn,
                                  no_match_rates=no_match_rates)
            runner.do_ablation(cohort, "random_grouping", float(gs), fn, X, y,
                                seeds, n_splits, args.feature_set,
                                save_folds=True, no_match_rates=no_match_rates)
            if derived:
                log(f"{cohort}/random_grouping seed={gs}: derived kappa median "
                    f"{np.median(derived):.1f} over {len(derived)} folds")

        # --- reference: real patterns, same pre-specified kappa ---
        derived = []
        kappa_fn = _median_support_kappa(derived)
        no_match_rates = []
        fn = reference_fp(kappa=kappa_fn, no_match_rates=no_match_rates)
        runner.do_ablation(cohort, "reference", NO_VALUE, fn, X, y,
                            seeds, n_splits, args.feature_set,
                            save_folds=True, no_match_rates=no_match_rates)
        if derived:
            log(f"{cohort}/reference: derived kappa median "
                f"{np.median(derived):.1f} over {len(derived)} folds")

        # --- label-permutation control: coverage-matched by construction ---
        # (Task 16's replacement for random_grouping.) save_folds=True +
        # no_match_rates: same contract as the reference/random_grouping arms
        # -- Finding 1's paired test and Finding 2's no-match check both need
        # this arm's per-fold scores and no-match rate.
        for ps in perm_seeds:
            derived = []
            kappa_fn = _median_support_kappa(derived)
            no_match_rates = []
            fn = permuted_label_fp(perm_seed=ps, kappa=kappa_fn,
                                    no_match_rates=no_match_rates)
            runner.do_ablation(cohort, "label_permutation", float(ps), fn, X, y,
                                seeds, n_splits, args.feature_set,
                                save_folds=True, no_match_rates=no_match_rates)
            if derived:
                log(f"{cohort}/label_permutation seed={ps}: derived kappa median "
                    f"{np.median(derived):.1f} over {len(derived)} folds")

        # --- matched-ness diagnostic: structure only, quantifies the confound ---
        runner.do_matchedness(cohort, X, y, args.feature_set,
                               min_support=30, group_seeds=group_seeds)

    log("=== falsification check: random_grouping vs reference ===")
    runner.report_falsification(args.feature_set)

    log("=== falsification check: label_permutation vs reference (Task 16) ===")
    runner.report_falsification_permutation(args.feature_set)

    total_elapsed = time.time() - t_start
    log(f"=== run complete in {total_elapsed / 60:.1f} min ===")

    if runner.failures:
        log(f"=== {len(runner.failures)} FAILURE(S) -- see {runner.failures_path} ===")
        for f in runner.failures:
            log(f"  [{f['stage']}] cohort={f['cohort']} unit={f['unit']} "
                f"feature_set={f['feature_set']}: {f['error']}")
        sys.exit(1)
    else:
        log("no failures")


if __name__ == "__main__":
    main()
