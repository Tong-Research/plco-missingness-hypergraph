"""H1-H4 with the ancestor-bias diagnostic and no-match reporting.

Tests four pre-registered hypotheses on real PLCO data:

    H1  the interior of the kappa path beats both limits (kappa=0 and
        kappa->inf). If the optimum sits at a limit, the method reduces to
        an existing one.
    H2  shrinking toward ancestors beats shrinking toward one global model
        AT MATCHED STRENGTH (a pre-specified per-cohort kappa, identical for
        both -- see ``_median_support_kappa`` below). THIS IS THE PAPER. Run
        first: if H2 fails, the containment hierarchy is decoration.
        Comparator: ``spsm_global`` (Stempfle et al.).
    H3  mask informativeness (iota, reported per cohort in
        ``results/gate.csv`` from Task 14 / ``run_gate.py``) is associated
        with the method's benefit over the baselines.
    H4  the interaction-expanded mask model (``mask_interaction_lr``, full
        strength on purpose) does not match the method. If it does, the
        method is an efficient reparametrisation of a known model class.

Alongside H2, ``HypergraphShrinkage.ancestor_discrepancy()`` is reported: if
H2 is negative it distinguishes "the containment order carries no useful
information" (low mean_abs_diff -- ancestors and descendants agree, shrinkage
just isn't helping) from "the order is informative but the ancestors
estimate a materially different quantity" (high mean_abs_diff -- omitted
variable bias, a fixable targeting problem). The per-cohort no-match rate
(``est.no_match_rate``, from ``predict_proba`` on the full fit) is reported
too.

Corrections to the Task 15 brief (which predates data profiling):
  - ``load_cohort`` takes ``feature_set="baseline"`` (default, PRIMARY) or
    ``"full"`` (sensitivity). This is a CLI flag here (``--feature-set``) so
    the sensitivity run is a re-invocation, never an edit.
  - Every output row carries ``feature_set`` and ``subsample_n`` so results
    from different invocations sharing the same CSV can never be
    misattributed.
  - Cohorts are subsampled to MAX_N=40,000, stratified and seeded IDENTICALLY
    for every method (mask_interaction_lr needs the cap: its design matrix is
    [X, m, m (x) X], d + d + d^2 columns -- verified 19.2 GB peak at n=40,000
    on baseline features; the full n would need ~60-70 GB against 32 GB
    available). The H4 baseline runs at full model strength regardless --
    the constraint is absorbed by subsampling rows, not weakening the model.

Task 15 kappa fix (post-mortem on the first full run, stopped after 5.6h):
  - The estimator shrinks toward ancestors by lambda = |S(e)| / (|S(e)| +
    kappa). Real median pattern support is ~2,000, so the old hardcoded
    kappa=10 for ``ours`` gave median lambda 0.995 -- 87% of patterns got
    essentially zero shrinkage. ``ours``, ``pattern_submodels`` (kappa=0, no
    shrinkage by construction) and ``spsm_global`` (also hardcoded kappa=10)
    all collapsed to the same no-shrinkage estimator and returned identical
    metrics to four decimal places: H2 was vacuous.
  - FULL_KAPPAS is now log-spaced to sample lambda evenly around that
    median support (see the comment above its definition) instead of
    jumping from mild shrinkage straight to total shrinkage.
  - The H1 kappa path now runs BOTH ``ours`` (target="ancestors") and
    ``spsm_global`` (target="global") at every grid point -- H2 is a claim
    about matched-strength comparison, so the two curves must be
    comparable at identical kappa, not just ``ours`` alone.
  - The main table's single operating point for ``ours``/``spsm_global`` is
    no longer a hardcoded constant. It is pre-specified (not tuned):
    kappa = median(|S(e)|) over the fitted patterns, computed from the
    TRAINING split inside each CV fold (never the full dataset -- see
    ``estimator.fit_predict``'s callable-``kappa`` path and
    ``_median_support_kappa`` below), which puts median lambda at exactly
    0.5. Because it is fixed by a rule stated in advance rather than chosen
    to maximise held-out performance, it needs no optimism/multiple-testing
    correction, unlike a kappa selected by peeking at CV metrics.

Robustness for an 8-10 hour job:
  - Results are written incrementally (append after each (cohort, method) or
    (cohort, kappa) unit), never accumulated in memory and flushed at the
    end.
  - Each unit of work is wrapped in try/except: a failure is logged and
    recorded, and the run continues. A summary of all failures prints at the
    end.
  - Progress is logged with timestamps and per-unit elapsed time.
  - The run is resumable: if an output row for a (cohort, method,
    feature_set) [or (cohort, kappa, feature_set) / (cohort, feature_set)]
    already exists in its CSV, that unit of work is skipped. ``--force``
    recomputes everything.

Paired significance testing (``paired_holm``) runs WITHIN each cohort only,
filtered to the CURRENT invocation's ``--feature-set`` -- AUPRC is not
comparable across cohorts (different prevalences), and mixing feature sets in
one paired test would create duplicate (seed, fold) keys for the same method
(a real correctness bug the protocol module deliberately guards against; see
``protocol.paired_holm``'s docstring). Output is
``results/paired_{cohort}_{feature_set}.csv``.

``paired_holm`` raises if a comparison has fewer than 2 usable paired folds,
or on duplicate (seed, fold) keys -- both are deliberate guards against
silently invalid comparisons. Those exceptions are allowed to propagate out
of ``paired_holm`` itself; this script catches them only at the per-cohort
boundary, logs which cohort and comparison failed and why, and continues to
the next cohort -- so one invalid comparison does not hide the others and
does not abort the whole run.
"""

from __future__ import annotations

import os

import argparse
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from hgmiss import estimator
from hgmiss.baselines.native import histgb_native
from hgmiss.baselines.pattern import pattern_submodels, spsm_global
from hgmiss.baselines.simple import (
    mask_interaction_lr,
    mean_impute_lr,
    mean_indicator_lr,
)
from hgmiss.data.plco import COHORTS, FEATURE_SETS, load_cohort
from hgmiss.protocol import paired_holm, run_cv

# Resolve the dataset root RELATIVE to this file, not from a hardcoded absolute path.
# The default used to be "/Users/tong/Works/tong/phd/datasets/plco", which is correct on
# pilot and wrong on every other host. That single line caused a cascade on 2026-08-24:
# jobs written with PLCO_ROOT=$HOME/phd/... ran on spinner and failed on pilot, jobs written
# without it ran on pilot and failed on spinner, and each failure looked like a different
# bug. A repo-relative default is right on both, and PLCO_ROOT still overrides it for a
# dataset kept outside the tree.
#   experiments/ -> paper-plco-hypergraph/ -> papers/ -> <repo>
_REPO = Path(__file__).resolve().parents[3]
ROOT = Path(os.environ.get("PLCO_ROOT", _REPO / "datasets" / "plco"))

# Full-strength configuration (see module docstring for the memory rationale).
FULL_SEEDS = list(range(10))
# Log-spaced to sample lambda = |S(e)| / (|S(e)| + kappa) evenly given the
# real median pattern support (~2,000 rows), rather than the old linear-ish
# grid [0, 1, 3, 10, 30, 100, 300, 1e6] whose lambda barely moved off 1.0
# until the last point. Median lambda at each kappa (real PLCO data, median
# support ~2,000):
#   kappa        0     200    500   1,000  2,000  5,000  10,000  50,000  1e6
#   median lambda 1.00  0.91   0.80   0.67   0.50   0.29   0.17    0.04  0.002
FULL_KAPPAS = [0.0, 200.0, 500.0, 1_000.0, 2_000.0, 5_000.0, 10_000.0, 50_000.0, 1e6]
FULL_MAX_N = 40_000
FULL_N_SPLITS = 5

# Drastically reduced configuration for --smoke: verifies the whole pipeline
# (H2 first, H1 kappa path, remaining baselines, diagnostics, paired tests,
# incremental writes, resumability) executes end to end in well under a
# minute, before committing to an 8-10 hour run. Uses ALL methods (not a
# strict subset) -- the point of a smoke test is to exercise every code path,
# including the memory-heavy mask_interaction_lr, at a scale where a bug
# surfaces in seconds rather than hours in. Restricted to "prostate", the
# smallest cohort (fewest features, fewest rows), to keep it fast.
SMOKE_SEEDS = [0]
# A subset of FULL_KAPPAS spanning the same range (including a mid-grid
# point) so the smoke test exercises the same code path as the full run.
SMOKE_KAPPAS = [0.0, 2_000.0, 1e6]
SMOKE_MAX_N = 1_500
SMOKE_N_SPLITS = 2
SMOKE_COHORTS = ["prostate"]


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def _subsample(c, seed: int = 0, max_n: int = FULL_MAX_N):
    """Stratified subsample to ``max_n``, identical rows for every method.

    Returns the data unchanged if the cohort is already at or below the cap.
    """
    if c.X.shape[0] <= max_n:
        return c.X, c.y
    idx = np.arange(c.X.shape[0])
    keep, _ = train_test_split(
        idx, train_size=max_n, stratify=c.y, random_state=seed
    )
    return c.X[keep], c.y[keep]


def _method_registry():
    """Rebuilt per invocation: ``estimator.fit_predict`` closures are cheap
    and stateless, but constructing them fresh avoids any chance of shared
    mutable state across cohorts.

    ``ours`` and ``spsm_global`` are NOT here -- their main-table entries use
    a pre-specified, per-fold-derived kappa (see ``_median_support_kappa``
    and the H2-first block in ``main()``), not a module-level constant, so
    they are built there instead.
    """
    return {
        "pattern_submodels": pattern_submodels,  # H1 lower limit (kappa=0)
        "mask_interaction": mask_interaction_lr,  # H4 -- the dangerous one
        "mean_indicator": mean_indicator_lr,
        "mean_impute": mean_impute_lr,
        "histgb_native": histgb_native,
    }


def _median_support_kappa(recorded: list[float]):
    """Callable ``kappa(supports) -> float`` for ``estimator.fit_predict`` /
    ``spsm_global``: the pre-specified main-table operating point.

    kappa = median(|S(e)|) over the fitted patterns puts median lambda =
    |S(e)| / (|S(e)| + kappa) at exactly 0.5 -- a neutral midpoint between no
    shrinkage (lambda=1) and total shrinkage (lambda=0). It is set a priori
    by this rule, not chosen by maximising CV performance, so it needs no
    optimism correction. ``supports`` is computed from the TRAINING fold
    only (enforced by ``estimator.fit_predict``/``spsm_global``, which never
    see the held-out rows). Every derived value is appended to ``recorded``
    so the caller can log what was actually used per cohort, across the
    seeds x folds it was invoked for.
    """
    def _kappa(supports: dict) -> float:
        k = float(np.median(list(supports.values())))
        recorded.append(k)
        return k
    return _kappa


MAIN_COLUMNS = [
    "cohort", "method", "feature_set", "subsample_n", "seed", "fold",
    "auroc", "auprc", "prevalence", "accuracy", "brier",
    "calibration_slope", "calibration_intercept", "n_positive",
]
KAPPA_COLUMNS = [
    "cohort", "target", "kappa", "feature_set", "subsample_n", "auprc", "auprc_sd",
]
BIAS_COLUMNS = [
    "cohort", "feature_set", "subsample_n",
    "pattern_size", "ancestor_size", "n_shared", "mean_abs_diff",
]
NOMATCH_COLUMNS = ["cohort", "feature_set", "subsample_n", "no_match_rate"]
FAILURE_COLUMNS = ["timestamp", "stage", "cohort", "unit", "feature_set", "error"]


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

    Under normal (non-``--force``) operation the caller only reaches here
    when the key was NOT already present, so the drop is a no-op -- this is
    still an incremental, one-unit-at-a-time write, not a full-run
    accumulate-then-flush. It matters under ``--force``: a plain append would
    leave both the old and the recomputed rows in the file, silently
    duplicating (seed, fold) keys for the same method and corrupting
    ``paired_holm``'s guard against exactly that. The rewrite cost is
    negligible -- these are aggregate metric/diagnostic rows (thousands at
    most), never participant-level data.
    """
    new_df = new_df.reindex(columns=columns)
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path)
        # `match` is True only for rows equal to this key on EVERY key
        # column; we drop those and keep everything else. (Do not build
        # this as an AND of per-column `!=` -- that drops a row as soon as
        # ANY single column matches, which wipes out every OTHER method's
        # rows too whenever cohort/feature_set -- shared across methods --
        # happens to match.)
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
        self.main_path = self.out / "main.csv"
        self.kappa_path = self.out / "h1_kappa_path.csv"
        self.bias_path = self.out / "ancestor_bias.csv"
        self.nomatch_path = self.out / "nomatch.csv"
        self.failures_path = self.out / "failures.csv"

        self.done_main = _load_done(self.main_path, ["cohort", "method", "feature_set"])
        self.done_kappa = _load_done(self.kappa_path, ["cohort", "target", "kappa", "feature_set"])
        self.done_diag = _load_done(self.nomatch_path, ["cohort", "feature_set"])
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

    # -- main (H2 + remaining baselines) -------------------------------
    def do_method(self, cohort, method, fn, X, y, seeds, n_splits, feature_set,
                  n_jobs=1) -> None:
        key = (cohort, method, feature_set)
        if key in self.done_main and not self.force:
            log(f"skip [main] {cohort}/{method}/{feature_set} (already present)")
            return
        t0 = time.time()
        try:
            df = run_cv(fn, X, y, seeds=seeds, n_splits=n_splits, n_jobs=n_jobs)
            df["cohort"] = cohort
            df["method"] = method
            df["feature_set"] = feature_set
            df["subsample_n"] = X.shape[0]
            _upsert_csv(self.main_path, df, MAIN_COLUMNS,
                        ["cohort", "method", "feature_set"], key)
            self.done_main.add(key)
            elapsed = time.time() - t0
            log(f"done [main] {cohort}/{method}/{feature_set} "
                f"({len(seeds)} seeds x {n_splits} folds) in {elapsed:.1f}s")
        except Exception as exc:  # noqa: BLE001 -- deliberate: log and continue
            self.record_failure("main", cohort, method, feature_set, exc)

    # -- H1 kappa path (fit-once, sweep-all-kappas) ------------------------
    def do_kappa_sweep(self, cohort, kappas, X, y, seeds, n_splits, feature_set,
                       n_jobs=1) -> None:
        """The whole kappa path, fitting the per-pattern LogisticRegression
        models ONCE per (seed, fold) and re-shrinking for every kappa x target.

        This is EXACT memoization of ``do_kappa``, not an approximation: the raw
        per-pattern fits (``raw_theta_``/``supports_``/``ancestors_``/``scaler_``)
        are kappa-independent and deterministic given (X_tr, y_tr), so caching
        them and re-running only ``shrink`` + ``predict_proba`` per kappa yields
        bit-identical AUPRC to fitting fresh at each kappa -- verified before
        deploy. Both targets are computed from the same cached fit:
          - ``ancestors`` = ``shrink(raw, supports, ancestors, kappa)`` (== ours)
          - ``global``    = the shrink-to-root rebuild from ``spsm_global``.
        ~1.9x faster on the kappa path (the raw fit dominates; predict remains).
        """
        from sklearn.model_selection import StratifiedKFold

        from hgmiss.estimator import HypergraphShrinkage
        from hgmiss.metrics import evaluate
        from hgmiss.shrinkage import shrink

        want = {(cohort, t, float(k), feature_set)
                for k in kappas for t in ("ancestors", "global")}
        if want <= self.done_kappa and not self.force:
            log(f"skip [h1-sweep] {cohort}/{feature_set} (all kappa rows present)")
            return
        t0 = time.time()
        y = np.asarray(y).ravel()
        kfs = [float(k) for k in kappas]

        def _sweep_fold(tr, te):
            """All (target, kappa) AUPRCs for one fold, raw fit cached once.
            BLAS pinned single-thread so parallel folds don't oversubscribe."""
            from threadpoolctl import threadpool_limits
            with threadpool_limits(limits=1):
                est = HypergraphShrinkage(kappa=0.0, min_support=30).fit(X[tr], y[tr])
                yte = y[te]
                out = {}
                for kf in kfs:
                    if not est.raw_theta_:
                        p_anc = p_glob = np.full(len(te), est.prior_)
                    else:
                        est.theta_ = shrink(est.raw_theta_, est.supports_,
                                            est.ancestors_, kf)
                        p_anc = est.predict_proba(X[te])
                        root = min(est.patterns_, key=len)
                        gt = est.raw_theta_[root]
                        rebuilt = {}
                        for e, own in est.raw_theta_.items():
                            n_e = est.supports_[e]
                            lam = n_e / (n_e + kf) if (n_e + kf) > 0 else 0.0
                            rebuilt[e] = {key: (lam * v + (1 - lam) * gt[key])
                                          if key in gt else v
                                          for key, v in own.items()}
                        est.theta_ = rebuilt
                        p_glob = est.predict_proba(X[te])
                    out[("ancestors", kf)] = evaluate(yte, p_anc)["auprc"]
                    out[("global", kf)] = evaluate(yte, p_glob)["auprc"]
            return out

        try:
            splits = []
            for seed in seeds:
                cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
                splits.extend(cv.split(X, y))
            if n_jobs == 1:
                fold_results = [_sweep_fold(tr, te) for tr, te in splits]
            else:
                from joblib import Parallel, delayed
                fold_results = Parallel(n_jobs=n_jobs, backend="loky")(
                    delayed(_sweep_fold)(tr, te) for tr, te in splits)
            acc = {(t, kf): [] for kf in kfs for t in ("ancestors", "global")}
            for fr in fold_results:
                for tk, v in fr.items():
                    acc[tk].append(v)

            # Keep the per-cell values, not just their mean. They are computed here and were
            # being discarded, which left H1's only artefact holding 18 rows of means -- and the
            # protocol pairs within (seed, fold) and forbids scoring on means, so H1 could not be
            # tested to this project's own standard from its own output (Result 131). splits was
            # built seed-major, so fold_results[i] belongs to seeds[i // n_splits], fold
            # i % n_splits.
            try:
                cells = []
                for i, fr in enumerate(fold_results):
                    s_i, f_i = seeds[i // n_splits], i % n_splits
                    for (tgt, kf), v in fr.items():
                        cells.append({"cohort": cohort, "target": tgt, "kappa": kf,
                                      "feature_set": feature_set, "seed": int(s_i),
                                      "fold": int(f_i), "auprc": float(v)})
                if cells:
                    cell_path = self.kappa_path.parent / "h1_kappa_cells.csv"
                    df = pd.DataFrame(cells)
                    if cell_path.exists():
                        prev = pd.read_csv(cell_path)
                        df = pd.concat([prev, df], ignore_index=True).drop_duplicates(
                            subset=["cohort", "target", "kappa", "feature_set", "seed", "fold"],
                            keep="last")
                    df.to_csv(cell_path, index=False)
                    log(f"  wrote {len(cells)} per-cell kappa rows to {cell_path.name}")
            except Exception as exc:                                        # noqa: BLE001
                # Never let the per-cell extra cost the sweep itself -- the mean file is what
                # existing consumers read.
                log(f"  per-cell kappa write failed (means still written): {exc!r}")
            for (t, kf), vals in sorted(acc.items()):
                v = np.asarray(vals, dtype=float)
                key = (cohort, t, kf, feature_set)
                row = pd.DataFrame([{
                    "cohort": cohort, "target": t, "kappa": kf,
                    "feature_set": feature_set, "subsample_n": X.shape[0],
                    "auprc": float(np.nanmean(v)), "auprc_sd": float(np.nanstd(v)),
                }])
                _upsert_csv(self.kappa_path, row, KAPPA_COLUMNS,
                            ["cohort", "target", "kappa", "feature_set"], key)
                self.done_kappa.add(key)
            log(f"done [h1-sweep] {cohort}/{feature_set} "
                f"({len(seeds)} seeds x {n_splits} folds x {len(kappas)} kappas x 2 "
                f"targets, fit cached) in {time.time() - t0:.1f}s")
        except Exception as exc:  # noqa: BLE001
            self.record_failure("h1_sweep", cohort, "all", feature_set, exc)

    def do_kappa(self, cohort, target, kappa, X, y, seeds, n_splits, feature_set) -> None:
        """``target`` is ``"ancestors"`` (``ours``, the proposed estimator) or
        ``"global"`` (``spsm_global``, H2's comparator) -- both run at every
        grid point so the two curves are comparable at matched kappa.

        Kept for reference / verification; ``main`` now uses ``do_kappa_sweep``,
        which is exact memoization of this and ~1.9x faster."""
        key = (cohort, target, kappa, feature_set)
        if key in self.done_kappa and not self.force:
            log(f"skip [h1] {cohort}/{target}/kappa={kappa}/{feature_set} (already present)")
            return
        t0 = time.time()
        try:
            if target == "ancestors":
                fn = estimator.fit_predict(kappa=kappa)
            elif target == "global":
                fn = lambda X_tr, y_tr, X_te, _k=kappa: spsm_global(X_tr, y_tr, X_te, kappa=_k)  # noqa: E731
            else:
                raise ValueError(f"unknown target {target!r}")
            df = run_cv(fn, X, y, seeds=seeds, n_splits=n_splits)
            row = pd.DataFrame([{
                "cohort": cohort, "target": target, "kappa": kappa,
                "feature_set": feature_set, "subsample_n": X.shape[0],
                "auprc": df.auprc.mean(), "auprc_sd": df.auprc.std(),
            }])
            _upsert_csv(self.kappa_path, row, KAPPA_COLUMNS,
                        ["cohort", "target", "kappa", "feature_set"], key)
            self.done_kappa.add(key)
            elapsed = time.time() - t0
            log(f"done [h1] {cohort}/{target}/kappa={kappa}/{feature_set} in {elapsed:.1f}s")
        except Exception as exc:  # noqa: BLE001
            self.record_failure("h1_kappa", cohort, f"{target}/kappa={kappa}", feature_set, exc)

    # -- diagnostics: ancestor discrepancy + no-match rate -----------------
    def do_diagnostics(self, cohort, X, y, feature_set) -> None:
        key = (cohort, feature_set)
        if key in self.done_diag and not self.force:
            log(f"skip [diagnostics] {cohort}/{feature_set} (already present)")
            return
        t0 = time.time()
        try:
            est = estimator.HypergraphShrinkage(kappa=10.0).fit(X, y)
            est.predict_proba(X)
            d = est.ancestor_discrepancy()
            if d.empty:
                log(f"note: {cohort}/{feature_set} has no ancestor-descendant "
                    f"pairs among realised patterns -- writing a placeholder row")
                d = pd.DataFrame([{
                    "pattern_size": np.nan, "ancestor_size": np.nan,
                    "n_shared": np.nan, "mean_abs_diff": np.nan,
                }])
            d["cohort"] = cohort
            d["feature_set"] = feature_set
            d["subsample_n"] = X.shape[0]
            _upsert_csv(self.bias_path, d, BIAS_COLUMNS,
                        ["cohort", "feature_set"], key)

            nomatch = pd.DataFrame([{
                "cohort": cohort, "feature_set": feature_set,
                "subsample_n": X.shape[0], "no_match_rate": est.no_match_rate,
            }])
            _upsert_csv(self.nomatch_path, nomatch, NOMATCH_COLUMNS,
                        ["cohort", "feature_set"], key)
            self.done_diag.add(key)
            elapsed = time.time() - t0
            log(f"done [diagnostics] {cohort}/{feature_set}: "
                f"no_match_rate={est.no_match_rate:.4f} in {elapsed:.1f}s")
            if est.no_match_rate > 0.05:
                log(f"WARNING: {cohort}/{feature_set} no_match_rate "
                    f"{est.no_match_rate:.2%} exceeds 5%")
        except Exception as exc:  # noqa: BLE001
            self.record_failure("diagnostics", cohort, "ancestor_discrepancy", feature_set, exc)

    # -- paired significance tests -----------------------------------------
    def do_paired_tests(self, feature_set: str) -> None:
        if not self.main_path.exists() or self.main_path.stat().st_size == 0:
            log("no main.csv rows yet -- skipping paired tests")
            return
        main_df = pd.read_csv(self.main_path)
        sub_all = main_df[main_df.feature_set == feature_set]
        for cohort in sorted(sub_all.cohort.unique()):
            sub = sub_all[sub_all.cohort == cohort]
            try:
                res = paired_holm(sub, reference="ours", metric="auprc")
            except Exception as exc:  # noqa: BLE001 -- reported, not swallowed
                self.record_failure("paired", cohort, "paired_holm(ref=ours)", feature_set, exc)
                continue
            res["cohort"] = cohort
            res["feature_set"] = feature_set
            out_path = self.out / f"paired_{cohort}_{feature_set}.csv"
            res.to_csv(out_path, index=False)
            log(f"paired tests written: {out_path}")
            print(res.to_string(index=False))


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feature-set", choices=FEATURE_SETS, default="baseline",
                    help="baseline (default, PRIMARY analysis) or full (sensitivity)")
    p.add_argument("--force", action="store_true",
                    help="recompute even if an output row already exists")
    p.add_argument("--smoke", action="store_true",
                    help="drastically reduced config for end-to-end verification")
    p.add_argument("--out-dir", default="results", help="output directory")
    p.add_argument("--methods", default=None,
                   help="comma-separated main-table methods to run, e.g. 'ours,mean_impute'. "
                        "Implies skipping the kappa sweep and diagnostics, which are not "
                        "methods. Unknown names are an error, so a typo cannot silently "
                        "select nothing and look like a clean run.")
    p.add_argument("--kappa-only", action="store_true",
                   help="run ONLY the H1 kappa sweep and write h1_kappa_cells.csv, skipping "
                        "every main-table method. The complement of --methods, which skips the "
                        "sweep; the two are mutually exclusive. Exists because the sweep is all "
                        "lung and colorectal still need, and a full run would redo "
                        "mask_interaction, which took 12h40 on colorectal.")
    p.add_argument("--cohort", choices=sorted(COHORTS), default=None,
                    help="restrict to ONE cohort (for parallel per-cohort runs "
                         "into separate --out-dir; results merge by concatenation)")
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Fold-level parallelism (each worker runs single-threaded BLAS). Tune via
    # env so the launch topology can change without editing code:
    #   HGMISS_NJOBS      -- workers for the light per-pattern methods + kappa
    #   HGMISS_NJOBS_MASK -- workers for mask_interaction (memory-heavy: its
    #                        design matrix is tens of GB/fold, so keep this low)
    n_jobs = int(os.environ.get("HGMISS_NJOBS", "1"))
    n_jobs_mask = int(os.environ.get("HGMISS_NJOBS_MASK", "1"))
    log(f"fold parallelism: n_jobs={n_jobs} (mask_interaction={n_jobs_mask})")

    if args.smoke:
        cohorts = SMOKE_COHORTS
        seeds = SMOKE_SEEDS
        kappas = SMOKE_KAPPAS
        max_n = SMOKE_MAX_N
        n_splits = SMOKE_N_SPLITS
        log(f"SMOKE MODE: cohorts={cohorts} seeds={seeds} kappas={kappas} "
            f"max_n={max_n} n_splits={n_splits}")
        if args.cohort and args.cohort not in SMOKE_COHORTS:
            # Silently ignoring a flag that was explicitly passed is how a run comes back
            # answering a different question than the one asked. Say it out loud.
            log(f"WARNING: --cohort {args.cohort} IGNORED under --smoke, which is pinned to "
                f"{SMOKE_COHORTS}. Drop --smoke to run {args.cohort}.")
    else:
        cohorts = [args.cohort] if args.cohort else sorted(COHORTS)
        seeds = FULL_SEEDS
        kappas = FULL_KAPPAS
        max_n = FULL_MAX_N
        n_splits = FULL_N_SPLITS

    kappa_seeds = seeds[:3] if not args.smoke else seeds[:1]

    runner = Runner(out, args.force)
    # Validate --methods before any cohort is loaded. Loading colorectal takes minutes, and a
    # typo should not cost them.
    if args.kappa_only and args.methods:
        raise SystemExit("  --kappa-only runs the sweep alone; --methods runs methods and "
                         "skips the sweep. Passing both asks for two different runs.")
    only = None
    if args.methods:
        only = {s.strip() for s in args.methods.split(",") if s.strip()}
        known = set(_method_registry()) | {"ours", "spsm_global"}
        unknown = only - known
        if unknown:
            raise SystemExit(f"unknown method(s) {sorted(unknown)}; known: {sorted(known)}")
        log(f"--methods: running only {sorted(only)}; skipping kappa sweep and diagnostics")

    t_start = time.time()

    for cohort in cohorts:
        log(f"=== loading {cohort} (feature_set={args.feature_set}) ===")
        c = load_cohort(cohort, ROOT, feature_set=args.feature_set)
        X, y = _subsample(c, seed=0, max_n=max_n)
        log(f"{cohort}: n={X.shape[0]:,} (of {c.X.shape[0]:,}) d={X.shape[1]} "
            f"prev={y.mean():.2%} feature_set={c.feature_set}")

        methods = _method_registry()

        # --methods narrows the main table. The cost spread across methods is four orders of
        # magnitude (mean_impute 8.6s, mask_interaction 53,555s), so a question about one
        # method should not have to buy all seven.
        if only is not None:
            methods = {k: v for k, v in methods.items() if k in only}

        # --- H2 FIRST: direction of shrinkage at matched strength ---
        # kappa is pre-specified (median training-fold pattern support ->
        # median lambda 0.5), derived fresh inside each CV fold -- never
        # from the full dataset. See _median_support_kappa.
        for label in ("ours", "spsm_global"):
            if only is not None and label not in only:
                continue
            derived: list[float] = []
            kappa_fn = _median_support_kappa(derived)
            if label == "ours":
                fn = estimator.fit_predict(kappa=kappa_fn)
            else:
                fn = lambda X_tr, y_tr, X_te, _k=kappa_fn: spsm_global(X_tr, y_tr, X_te, kappa=_k)  # noqa: E731
            if not args.kappa_only:
                runner.do_method(cohort, label, fn, X, y, seeds, n_splits,
                                 args.feature_set, n_jobs=n_jobs)
            if derived:
                log(f"{cohort}/{label}: pre-specified kappa (median training-fold "
                    f"support, median lambda=0.5) -- median {np.median(derived):.1f} "
                    f"over {len(derived)} folds (range {min(derived):.1f}-{max(derived):.1f})")

        # --- H1: the kappa path, both targets at every grid point ---
        # Fit-once-per-fold, sweep all kappas (exact memoization of do_kappa).
        if only is None:
            runner.do_kappa_sweep(cohort, kappas, X, y, kappa_seeds, n_splits,
                                  args.feature_set, n_jobs=n_jobs)

        # --- remaining baselines (includes H4's mask_interaction) ---
        # mask_interaction's design matrix is tens of GB per fold, so it must
        # NOT fold-parallelise at the light-method width -- cap it hard.
        for label, fn in methods.items():
            if args.kappa_only:
                continue
            m_jobs = n_jobs_mask if label == "mask_interaction" else n_jobs
            runner.do_method(cohort, label, fn, X, y, seeds, n_splits,
                             args.feature_set, n_jobs=m_jobs)

        # --- diagnostics on a full fit: ancestor discrepancy + no-match ---
        if only is None:
            runner.do_diagnostics(cohort, X, y, args.feature_set)

    log("=== paired tests, within cohort, current feature_set only ===")
    runner.do_paired_tests(args.feature_set)

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
