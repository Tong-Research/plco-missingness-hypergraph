#!/usr/bin/env python3
"""Ingest raw experiment CSVs into the two CSVs the figure/table generators
consume (``real_results.csv`` and ``real_cohorts.csv``), mirroring the
column layout of ``mock_results.csv`` / ``mock_cohorts.csv`` exactly.

This module deliberately does NOT touch ``make_figures.py`` or
``make_tables.py`` -- those own the MOCK-vs-real switch and presentation.
Its only job is to produce correctly-shaped ``real_*.csv`` files from the
raw experiment output in ``results/``.

Inputs (written by the experiment, under ``results/``):
  main.csv     -- long, one row per cohort x method x seed x fold:
                   cohort, method, feature_set, subsample_n, seed, fold,
                   auroc, auprc, prevalence, accuracy, brier,
                   calibration_slope, calibration_intercept, n_positive
  nomatch.csv  -- one row per cohort x feature_set:
                   cohort, feature_set, subsample_n, no_match_rate
  real_cohorts.csv (already produced elsewhere) -- one row per cohort x
                   feature_set: cohort, feature_set, n_full, subsample_n, d,
                   prevalence, missing_rate, n_patterns, median_support_ratio

Outputs (under ``figures/``):
  real_results.csv -- wide, one row per method (see RESULTS_COLUMNS).
  real_cohorts.csv -- one row per cohort (see COHORTS_COLUMNS).

The transform logic lives in pure functions (``build_results_table``,
``build_cohorts_table``) that take/return DataFrames so it is unit-testable
without touching the filesystem or any real (DTA-governed) data. ``main()``
is a thin driver that reads real files from disk and writes the outputs --
it is exercised manually against a live run, not by the test suite.
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from hgmiss.metrics import logit_ci

# ---------------------------------------------------------------------------
# Fixed, documented method -> (family, display name) mapping.
#
# If ``main.csv`` ever contains a method not listed here, build_results_table
# raises rather than silently dropping it -- a new baseline must not vanish
# from the table unnoticed. Dict order also drives the within-family row
# order in the output (see build_results_table).
# ---------------------------------------------------------------------------
METHOD_MAP: dict[str, tuple[str, str]] = {
    "mean_impute": ("impute", "Mean + logistic"),
    "mask_interaction": ("mask", "Mean + indicator x features"),
    "mean_indicator": ("mask", "Mean + indicator"),
    "histgb_native": ("native", "HistGradientBoosting"),
    "spsm_global": ("pattern", "SPSM"),
    "pattern_submodels": ("pattern", "Pattern submodels"),
    # The six additional baselines, mapped to the families sections-experiment.tex's
    # \subsubsection{Baselines} already assigns them, so the table's grouping and the prose
    # agree. Adding them here rather than filtering them out: the loud failure that sent me
    # here exists precisely so a baseline cannot vanish from the table by omission.
    "mice_impute_lr": ("impute", "Chained equations"),
    "xgboost_native": ("native", "XGBoost"),
    "lightgbm_native": ("native", "LightGBM"),
    "learnpp_mf": ("pattern", "Learn++.MF"),
    "refe": ("pattern", "Reduced-feature ensemble"),
    "refe_tree": ("pattern", "Reduced-feature ensemble (tree)"),
    "ours": ("ours", "Proposed method"),
}

# Family display/row order. "ours" last, as in mock_results.csv.
FAMILY_ORDER: list[str] = ["impute", "mask", "native", "pattern", "ours"]

COHORTS: list[str] = ["colorectal", "lung", "ovarian", "prostate"]

RESULTS_COLUMNS: list[str] = (
    ["family", "method"]
    + COHORTS
    + [f"ci_{c}" for c in COHORTS]
    + [f"acc_{c}" for c in COHORTS]
    + [f"auroc_{c}" for c in COHORTS]
)

COHORTS_COLUMNS: list[str] = [
    "cohort",
    "n",
    "d",
    "pct_miss",
    "pct_pos",
    "patterns",
    "iota",
    "iota_ci",
    "fallback",
]

_ALPHA = 0.05


def _mean_and_ci(values: np.ndarray) -> tuple[float, float]:
    """Mean and half-width-of-95%-CI (logit scale) over finite values.

    Non-finite (NaN/inf) entries are dropped first. With zero finite values
    the mean is NaN; with fewer than two, the CI half-width is NaN (an empty
    cell downstream) rather than raising.
    """
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan"), float("nan")
    mean = float(finite.mean())
    if finite.size < 2:
        return mean, float("nan")
    lo, hi = logit_ci(finite, alpha=_ALPHA)
    return mean, (hi - lo) / 2


def _mean_only(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    return float(finite.mean())


# The full-run subsample size. Rows at any other size are smoke or partial output and are
# refused above; run_h1_h4.py's FULL_MAX_N must match this.
FULL_SUBSAMPLE_N = 40_000



def _out(base, name: str, feature_set: str):
    """`real_results.csv` for the primary analysis, `real_results_full.csv` for a sensitivity
    set. Without this, running the ingest for `full` overwrote every baseline table in place."""
    if feature_set == "baseline":
        return base / name
    stem, dot, ext = name.rpartition(".")
    return base / f"{stem}_{feature_set}.{ext}"

def load_main_frame(results_dir):
    """The per-fold frame every table and figure is built from.

    Extracted so the figures read the same files as the tables. The figure
    generator used to open results/main.csv alone, which is the failure the
    comment below already describes: of the seven methods in the main table,
    that file holds `ours` and `mean_impute` for prostate only, and two rows
    each. Every paired interval the figures drew was therefore either NaN,
    and silently omitted, or computed from two observations.
    """
    # Read every committed result file, not just main.csv. main.csv lost 1,850 rows on
    # 2026-08-24 and the rebuilt cohorts live in results/rebuild-*/main.csv, with the extra
    # baselines in results/main_*.csv. Reading only main.csv produced a table of eight rows in
    # which almost every cell was empty -- which would have reached the paper as a table of
    # blanks rather than as an error, because the generator has no way to tell "this method
    # was not run" from "this method's file was not read".
    _sources = [results_dir / "main.csv",
                *sorted(results_dir.glob("main_*.csv")),
                *sorted(results_dir.glob("rebuild-*/main.csv")),
                # the full-feature-set sensitivity analysis: FULL-<cohort>/main.csv carries the
                # seven main-table methods, FULLX-<cohort>.csv the six extra baselines. Both
                # carry feature_set="full", so build_results_table's filter separates them from
                # the primary analysis; they were invisible here until 2026-09-02.
                *sorted(results_dir.glob("FULL-*/main.csv")),
                *sorted(results_dir.glob("FULLX-*.csv"))]
    _frames = []
    for _s in _sources:
        if not _s.exists():
            continue
        try:
            _d = pd.read_csv(_s)
        except Exception:                                            # noqa: BLE001
            continue
        if {"cohort", "method", "auprc", "seed", "fold"} <= set(_d.columns):
            _frames.append(_d)
    if not _frames:
        raise SystemExit(f"no usable result files under {results_dir}")
    main_df = pd.concat(_frames, ignore_index=True)

    # Smoke output must never reach the paper. `run_h1_h4.py --smoke` writes real-looking rows at
    # subsample_n = 1500 (SMOKE_MAX_N) with seed 0 and folds 0-1, and four of them were sitting in
    # results/main.csv on 2026-08-27. They are indistinguishable from real rows on every column
    # the de-duplication key uses, and results/main.csv is FIRST in the source order, so
    # keep="first" kept the smoke rows and evicted the genuine rebuild rows for the same
    # (cohort, method, seed, fold). The paper would have quoted a 1,500-record smoke estimate as
    # a 40,000-record result. Dropped here rather than deleted at source, and reported rather
    # than dropped quietly -- a silent filter is how the next one goes unnoticed.
    if "subsample_n" in main_df.columns:
        _bad = main_df[main_df.subsample_n != FULL_SUBSAMPLE_N]
        if len(_bad):
            print(f"  DROPPED {len(_bad)} row(s) not at subsample_n={FULL_SUBSAMPLE_N:,} "
                  f"-- smoke or partial output, never paper input:")
            for (_c, _m, _n), _g in _bad.groupby(["cohort", "method", "subsample_n"]):
                print(f"    {_c}/{_m}: {len(_g)} row(s) at subsample_n={_n:,}")
            main_df = main_df[main_df.subsample_n == FULL_SUBSAMPLE_N]

    # feature_set is part of the identity. Without it, every full-feature-set row was discarded
    # as a duplicate of the baseline row with the same cohort, method, seed and fold -- the
    # baseline files come first in the source list -- and the sensitivity analysis silently
    # ingested as zero rows on 2026-09-02. Same class as the smoke-row bug above: a key blind
    # to the column that distinguishes the rows.
    main_df = main_df.drop_duplicates(
        subset=["cohort", "method", "feature_set", "seed", "fold"], keep="first")
    print(f"  read {len(_frames)} result file(s), {len(main_df):,} rows after de-duplication")
    return main_df


def build_results_table(main_df: pd.DataFrame, feature_set: str = "baseline") -> pd.DataFrame:
    """Long per-fold results -> wide per-method table (mirrors mock_results.csv).

    One row per method actually present in ``main_df`` for ``feature_set``.
    Bare cohort columns are mean AUPRC over the seed x fold estimates;
    ``ci_<cohort>`` is the half-width of its 95% CI (logit scale); ``acc_``
    is mean accuracy as a percentage; ``auroc_`` is mean AUROC.

    Raises ValueError naming the method if ``main_df`` contains a method not
    in METHOD_MAP.
    """
    df = main_df[main_df["feature_set"] == feature_set]

    methods_present = list(pd.unique(df["method"]))
    unknown = sorted(m for m in methods_present if m not in METHOD_MAP)
    if unknown:
        raise ValueError(
            f"Unknown method(s) {unknown!r} in main.csv are not in "
            "ingest_results.METHOD_MAP. Add a (family, display name) entry "
            "for each before it can appear in real_results.csv -- baselines "
            "must not silently vanish from the table."
        )

    method_rank = {m: i for i, m in enumerate(METHOD_MAP)}
    family_rank = {f: i for i, f in enumerate(FAMILY_ORDER)}

    rows = []
    for method in sorted(
        methods_present,
        key=lambda m: (family_rank[METHOD_MAP[m][0]], method_rank[m]),
    ):
        family, display_name = METHOD_MAP[method]
        sub = df[df["method"] == method]
        row = {"family": family, "method": display_name}
        for cohort in COHORTS:
            csub = sub[sub["cohort"] == cohort]
            auprc = csub["auprc"].to_numpy(dtype=float)
            mean_auprc, ci = _mean_and_ci(auprc)
            row[cohort] = mean_auprc
            row[f"ci_{cohort}"] = ci
            row[f"acc_{cohort}"] = _mean_only(csub["accuracy"].to_numpy(dtype=float)) * 100
            row[f"auroc_{cohort}"] = _mean_only(csub["auroc"].to_numpy(dtype=float))
        rows.append(row)

    return pd.DataFrame(rows, columns=RESULTS_COLUMNS)


def build_cohorts_table(
    stats_df: pd.DataFrame,
    nomatch_df: pd.DataFrame,
    feature_set: str = "baseline",
    iota: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Per-cohort stats + no-match rates -> cohort table (mirrors mock_cohorts.csv).

    ``iota`` is an optional ``{cohort: (iota, iota_ci)}`` map -- mask
    informativeness is not produced by the experiment pipeline and must be
    supplied separately (it requires loading real cohort data, which this
    module never does). When absent, the iota/iota_ci cells are left empty
    and a warning is issued.
    """
    stats = stats_df[stats_df["feature_set"] == feature_set]
    nomatch = nomatch_df[nomatch_df["feature_set"] == feature_set]

    if iota is None:
        warnings.warn(
            "build_cohorts_table: no `iota` mapping supplied -- mask "
            "informativeness must be computed separately from real cohort "
            "data and passed in as {cohort: (iota, iota_ci)}. Writing empty "
            "iota/iota_ci cells.",
            UserWarning,
            stacklevel=2,
        )

    order = {c: i for i, c in enumerate(COHORTS)}
    cohort_names = sorted(
        pd.unique(stats["cohort"]), key=lambda c: order.get(c, len(order))
    )

    rows = []
    for cohort in cohort_names:
        srow = stats[stats["cohort"] == cohort]
        if len(srow) != 1:
            raise ValueError(
                f"Expected exactly one real_cohorts.csv row for cohort="
                f"{cohort!r}, feature_set={feature_set!r}; found {len(srow)}."
            )
        srow = srow.iloc[0]

        nrow = nomatch[nomatch["cohort"] == cohort]
        if len(nrow) != 1:
            raise ValueError(
                f"Expected exactly one nomatch.csv row for cohort={cohort!r}, "
                f"feature_set={feature_set!r}; found {len(nrow)}."
            )
        fallback = float(nrow.iloc[0]["no_match_rate"])

        if iota is not None and cohort in iota:
            iota_val, iota_ci_val = iota[cohort]
        else:
            iota_val, iota_ci_val = float("nan"), float("nan")

        rows.append(
            {
                "cohort": str(cohort).capitalize(),
                "n": srow["n_full"],
                "d": srow["d"],
                "pct_miss": float(srow["missing_rate"]) * 100,
                "pct_pos": float(srow["prevalence"]) * 100,
                "patterns": srow["n_patterns"],
                "iota": iota_val,
                "iota_ci": iota_ci_val,
                "fallback": fallback,
            }
        )

    return pd.DataFrame(rows, columns=COHORTS_COLUMNS)



def build_spsm_pairs(main_df, feature_set: str, comparator: str = "spsm_global") -> "pd.DataFrame":
    """Paired ours-vs-SPSM statistics per cohort, from the per-cell data.

    make_tables.py previously carried SPSM_PAIR_CI = [0.009, 0.008, 0.012, 0.016], a hardcoded
    half-width invented alongside the mock table. It decided both the dagger that marks a tie and
    the significant-win count, so two of the table's three verdicts rested on numbers nobody
    measured.

    Computed here rather than read from results/paired_*.csv for two reasons: those files carry
    p_holm but no interval, and there are two competing versions for colorectal (pre-rebuild and
    rebuild) with no rule for choosing. Deriving it from the same de-duplicated frame the table is
    built from means the interval and the means cannot disagree.

    The interval is a 95% bootstrap CI on the MEDIAN paired difference, matching the protocol
    section, which pairs within (seed, fold) and reports an improvement only when the interval
    excludes zero. Holm correction is applied across the cohorts present, not a fixed four.
    """
    import numpy as np
    from scipy import stats

    rows = []
    for cohort, g in main_df[main_df.feature_set == feature_set].groupby("cohort"):
        piv = g.pivot_table(index=["seed", "fold"], columns="method", values="auprc")
        if not {"ours", comparator} <= set(piv.columns):
            continue
        pair = piv[["ours", comparator]].dropna()
        if len(pair) < 10:
            continue
        d = (pair["ours"] - pair[comparator]).to_numpy(float)
        rng = np.random.default_rng(0)          # fixed: the interval must not move between runs
        boot = np.median(rng.choice(d, size=(10000, len(d)), replace=True), axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        try:
            p_raw = float(stats.wilcoxon(d).pvalue)
        except ValueError:
            p_raw = float("nan")
        rows.append({"cohort": cohort, "n_pairs": len(d),
                     "median_diff": float(np.median(d)), "ci_lo": float(lo), "ci_hi": float(hi),
                     "ci_half": float((hi - lo) / 2), "p_raw": p_raw})
    if not rows:
        return pd.DataFrame(columns=["cohort", "n_pairs", "median_diff", "ci_lo", "ci_hi",
                                     "ci_half", "p_raw", "p_holm"])
    out = pd.DataFrame(rows).sort_values("p_raw").reset_index(drop=True)
    m = len(out)
    prev = 0.0
    holm = []
    for i, praw in enumerate(out.p_raw):
        v = min(1.0, max(prev, (m - i) * praw))
        holm.append(v)
        prev = v
    out["p_holm"] = holm
    return out.sort_values("cohort").reset_index(drop=True)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", default="baseline")
    parser.add_argument(
        "--results-dir",
        default=str(Path(__file__).resolve().parent.parent / "results"),
    )
    parser.add_argument(
        "--figures-dir", default=str(Path(__file__).resolve().parent)
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    figures_dir = Path(args.figures_dir)

    main_df = load_main_frame(results_dir)
    # The full-feature-set jobs write nomatch.csv into their own directories, so the root file
    # never sees them; read both, same schema.
    nomatch_df = pd.concat([pd.read_csv(results_dir / "nomatch.csv"),
                            *[pd.read_csv(f) for f in sorted(results_dir.glob("FULL-*/nomatch.csv"))]],
                           ignore_index=True)
    stats_df = pd.read_csv(results_dir / "real_cohorts.csv")

    # Mask informativeness, from run_gate.py. Until 2026-08-24 this was passed as None and the
    # cohorts table shipped with empty iota cells, while the abstract asserted iota for all four
    # cohorts -- a claim with no file behind it. gate.csv now exists, so it is read here.
    #
    # The CI is NaN on purpose. run_gate reports iota as a SINGLE cross-validated estimate and
    # computes no interval; its own docstring gives a measured sd of about 0.09 at n=600 and
    # 0.04 at n=2000, as guidance rather than as a per-cohort figure. Inventing an interval from
    # that would be fabricating precision the experiment did not produce.
    iota_map = None
    gate_path = results_dir / "gate.csv"
    if gate_path.exists():
        g = pd.read_csv(gate_path)
        g = g[(g["feature_set"] == args.feature_set) & (g["subsample"] == "n40000")]
        iota_map = {r.cohort: (float(r.iota), float("nan")) for r in g.itertuples()}
        if not iota_map:
            iota_map = None

    results_table = build_results_table(main_df, feature_set=args.feature_set)
    # A sensitivity set may be partial while its last cohort runs. The primary analysis keeps
    # the strict one-row-per-cohort contract; for any other feature set, cohorts whose rows have
    # not landed are skipped and NAMED, so a three-of-four table cannot pass as four.
    _present = set(main_df[main_df.feature_set == args.feature_set].cohort.unique())
    if args.feature_set != "baseline":
        _have = (set(stats_df[stats_df.feature_set == args.feature_set].cohort)
                 & set(nomatch_df[nomatch_df.feature_set == args.feature_set].cohort) & _present)
        _missing = sorted(_present - _have)
        if _missing:
            print(f"  feature_set={args.feature_set!r}: cohorts table SKIPS {_missing} -- "
                  f"rows not landed yet; the results tables still include them")
        stats_df = stats_df[~((stats_df.feature_set == args.feature_set) & ~stats_df.cohort.isin(_have))]
        nomatch_df = nomatch_df[~((nomatch_df.feature_set == args.feature_set) & ~nomatch_df.cohort.isin(_have))]
        # And drop those cohorts from the RESULTS frame for this feature set too. Left in, a
        # cohort holding one method makes that method rank first there, and every downstream
        # count -- ranks, Nemenyi, family pairs -- inherits a cohort that does not exist yet.
        # That is how \RankMain read "1--6" on 2026-09-02 with colorectal's 50-row stub in.
        _stub = main_df[(main_df.feature_set == args.feature_set) & ~main_df.cohort.isin(_have)]
        if len(_stub):
            print(f"  feature_set={args.feature_set!r}: DROPS {len(_stub)} result row(s) from "
                  f"{sorted(_stub.cohort.unique())} for every table -- partial cohort")
            main_df = main_df.drop(_stub.index)
    cohorts_table = build_cohorts_table(
        stats_df, nomatch_df, feature_set=args.feature_set, iota=iota_map
    )

    results_table.to_csv(_out(figures_dir, "real_results.csv", args.feature_set), index=False)
    cohorts_table.to_csv(_out(figures_dir, "real_cohorts.csv", args.feature_set), index=False)
    print(f"wrote {_out(figures_dir, 'real_results.csv', args.feature_set)}")
    print(f"wrote {_out(figures_dir, 'real_cohorts.csv', args.feature_set)}")

    pairs = build_spsm_pairs(main_df, feature_set=args.feature_set)
    pairs_path = _out(figures_dir, "real_spsm_pairs.csv", args.feature_set)
    pairs.to_csv(pairs_path, index=False)
    print(f"wrote {pairs_path}  ({len(pairs)} cohort(s) with both arms)")

    # Both within-family comparators in one file, so the experiment section's paragraph about
    # where the method DOES separate is generated rather than typed. Written separately from
    # real_spsm_pairs.csv so make_tables.py's input is untouched.
    _fam = []
    for _c in ("spsm_global", "pattern_submodels", "mask_interaction"):
        _p = build_spsm_pairs(main_df, feature_set=args.feature_set, comparator=_c)
        if len(_p):
            _p = _p.copy()
            _p.insert(0, "comparator", _c)
            _fam.append(_p)
    if _fam:
        _fam = pd.concat(_fam, ignore_index=True)
        _fam["x_floor"] = _fam.median_diff / 0.002
        _fam["ci_excludes_zero"] = ~((_fam.ci_lo <= 0) & (0 <= _fam.ci_hi))
        _fp = _out(figures_dir, "real_family_pairs.csv", args.feature_set)
        _fam.to_csv(_fp, index=False)
        print(f"wrote {_fp}  ({len(_fam)} comparator-cohort pair(s), "
              f"{int((~_fam.ci_excludes_zero).sum())} with a CI containing zero)")

        # Emit the LaTeX too. The experiment section had these numbers typed by hand, which is
        # the trap the H1 paragraph just walked into: a cohort lands, the table beside the prose
        # updates, and the prose keeps asserting the old count. Table and counts come from here.
        _NM = {"lung": "Lung", "colorectal": "Colorectal", "ovarian": "Ovarian",
               "prostate": "Prostate"}
        _CM = {"spsm_global": "SPSM", "pattern_submodels": "Pattern submodels",
               "mask_interaction": "Mask interaction"}

        def _p(v):
            t = f"{v:.2g}"
            if "e" in t:
                m, e = t.split("e")
                return f"${m}\\times10^{{{int(e)}}}$"
            return f"${t}$"

        _tab = Path(__file__).resolve().parent.parent / "tables"
        _tab.mkdir(exist_ok=True)
        _fam2 = _fam[_fam.comparator != "mask_interaction"]
        _L = ["% GENERATED by figures/ingest_results.py -- do not edit by hand.",
              r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
              r"Comparator & Cohort & Difference & 95\% CI & $p_{\text{Holm}}$ & $\times$ floor \\",
              r"\midrule"]
        for _c in ("spsm_global", "pattern_submodels"):
            _g = _fam2[_fam2.comparator == _c].sort_values("median_diff", ascending=False)
            for _i, (_, _r) in enumerate(_g.iterrows()):
                _lab = f"\\multirow{{{len(_g)}}}{{*}}{{{_CM[_c]}}}" if _i == 0 else ""
                _L.append(f"{_lab} & {_NM[_r.cohort]} & ${_r.median_diff:+.6f}$ & "
                          f"$[{_r.ci_lo:+.5f}, {_r.ci_hi:+.5f}]$ & {_p(_r.p_holm)} & "
                          f"${_r.x_floor:.2f}$ \\\\")
            if _c == "spsm_global":
                _L.append(r"\midrule")
        _L += [r"\bottomrule", r"\end{tabular}"]
        (_out(_tab, "family_pairs.tex", args.feature_set)).write_text("\n".join(_L) + "\n")
        print(f"wrote {_out(_tab, 'family_pairs.tex', args.feature_set)}")

        _mi = _fam[_fam.comparator == "mask_interaction"]
        _n_beat = int((_mi.median_diff < 0).sum())
        _worst = _mi.median_diff.min()
        (_out(_tab, "family_counts.tex", args.feature_set)).write_text(
            "% GENERATED by figures/ingest_results.py -- do not edit by hand.\n"
            f"\\newcommand{{\\FamPairs}}{{{len(_fam2)}}}\n"
            f"\\newcommand{{\\FamZero}}{{{int((~_fam2.ci_excludes_zero).sum())}}}\n"
            f"\\newcommand{{\\MaskCohorts}}{{{len(_mi)}}}\n"
            f"\\newcommand{{\\MaskBeats}}{{{_n_beat}}}\n"
            f"\\newcommand{{\\MaskWorst}}{{${abs(_worst):.3f}$}}\n"
            f"\\newcommand{{\\MaskWorstX}}{{{abs(_worst)/0.002:.1f}}}\n")
        print(f"wrote {_out(_tab, 'family_counts.tex', args.feature_set)}")

        # The main-table ordering, as macros. The prose said "seventh of twelve" against a table
        # of thirteen methods, and "the same ordering holds on Colorectal and Prostate" when the
        # method actually ranks better there than on Lung. Both were true of an earlier, smaller
        # run and became false without anyone editing them.
        _b = main_df[main_df.feature_set == args.feature_set]
        _MAIN7 = ["ours", "spsm_global", "pattern_submodels", "mean_impute",
                  "mean_indicator", "mask_interaction", "histgb_native"]
        _r7, _rall, _marg, _cells, _nall = [], [], [], [], set()
        for _coh, _g in _b.groupby("cohort"):
            _m = _g.groupby("method").auprc.mean().sort_values(ascending=False)
            if "ours" not in _m.index:
                continue
            _nall.add(len(_m))
            _sub = _m[_m.index.isin(_MAIN7)]
            _r7.append(list(_sub.index).index("ours") + 1)
            _rall.append(list(_m.index).index("ours") + 1)
            _pv = _g.pivot_table(index=["seed", "fold"], columns="method", values="auprc")
            if {"mean_impute", "ours"} <= set(_pv.columns):
                _d = (_pv["mean_impute"] - _pv["ours"]).dropna()
                _marg.append(float(_d.median()))
                _cells.append(int((_d > 0).sum()))

        def _rng(v, fmt="{:d}"):
            return fmt.format(min(v)) if min(v) == max(v) else f"{fmt.format(min(v))}--{fmt.format(max(v))}"

        (_out(_tab, "rank_counts.tex", args.feature_set)).write_text(
            "% GENERATED by figures/ingest_results.py -- do not edit by hand.\n"
            f"\\newcommand{{\\RankMain}}{{{_rng(_r7)}}}\n"
            f"\\newcommand{{\\RankMainOf}}{{{len(_MAIN7)}}}\n"
            f"\\newcommand{{\\RankAll}}{{{_rng(_rall)}}}\n"
            f"\\newcommand{{\\RankAllOf}}{{{max(_nall) if _nall else 0}}}\n"
            f"\\newcommand{{\\ImputeMarginLo}}{{${min(_marg):.4f}$}}\n"
            f"\\newcommand{{\\ImputeMarginHi}}{{${max(_marg):.4f}$}}\n"
            f"\\newcommand{{\\ImputeCellsLo}}{{{min(_cells)}}}\n"
            f"\\newcommand{{\\ImputeCellsHi}}{{{max(_cells)}}}\n"
            f"\\newcommand{{\\NCohorts}}{{{len(_r7)}}}\n")
        print(f"wrote {_out(_tab, 'rank_counts.tex', args.feature_set)}")

        # The Friedman/Nemenyi numbers the article uses to justify omitting a critical-difference
        # diagram. It asserted "the critical difference is approximately 6 rank positions, which
        # exceeds the range of the ranks. All methods would be reported as indistinguishable."
        # On the completed table that is false: CD is smaller than the observed spread, so the
        # diagram WOULD separate the extremes. What it cannot separate is the proposed method
        # from the imputation baselines, which is the honest version of the same point.
        _M = _b.groupby(["cohort", "method"]).auprc.mean().unstack()
        _k, _N = _M.shape[1], _M.shape[0]
        _ranks = _M.rank(axis=1, ascending=False)
        _mr = _ranks.mean().sort_values()
        # Demsar (2006) table 5: q_0.05, the studentised range divided by sqrt(2)
        _Q = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031,
              9: 3.102, 10: 3.164, 11: 3.219, 12: 3.268, 13: 3.313, 14: 3.354}
        _q = _Q.get(_k)
        if _q is not None and "ours" in _mr.index:
            _cd = _q * np.sqrt(_k * (_k + 1) / (6.0 * _N))
            _spread = float(_mr.max() - _mr.min())
            _gap = float(_mr["ours"] - _mr.min())
            (_out(_tab, "nemenyi_counts.tex", args.feature_set)).write_text(
                "% GENERATED by figures/ingest_results.py -- do not edit by hand.\n"
                f"\\newcommand{{\\NemK}}{{{_k}}}\n"
                f"\\newcommand{{\\NemN}}{{{_N}}}\n"
                f"\\newcommand{{\\NemCD}}{{${_cd:.1f}$}}\n"
                f"\\newcommand{{\\NemSpread}}{{${_spread:.1f}$}}\n"
                f"\\newcommand{{\\NemOursGap}}{{${_gap:.1f}$}}\n"
                f"\\newcommand{{\\NemOursRank}}{{${float(_mr['ours']):.2f}$}}\n")
            print(f"wrote {_out(_tab, 'nemenyi_counts.tex', args.feature_set)}  "
                  f"(CD {_cd:.2f} vs spread {_spread:.2f})")


if __name__ == "__main__":
    main()
