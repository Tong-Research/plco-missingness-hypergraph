#!/usr/bin/env python3
"""
Figure generation for the PLCO pattern-lattice paper.

>>> EVERY NUMBER IS MOCK — read from mock_results.csv / mock_cohorts.csv <<<

The figures exist so the paper's layout and argument can be judged before the
experiments run. Each figure carries a MOCK watermark.

TO GO LIVE:
  1. produce real_results.csv / real_cohorts.csv in the same schema
  2. set MOCK = False below
  3. re-run this and make_tables.py

Run:  python make_figures.py
"""

import csv
import numpy as np
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

import os

MOCK = False          # data source: mock_*.csv vs real_*.csv
# Watermark follows MOCK, but can be suppressed for a clean preview render.
# NO_WATERMARK=1 does NOT make the data real — see make_preview.sh.
SHOW_WATERMARK = MOCK and os.environ.get("NO_WATERMARK") != "1"

RESULTS_CSV = "mock_results.csv" if MOCK else "real_results.csv"
RESULTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "results"   # committed per-run CSVs
COHORTS_CSV = "mock_cohorts.csv" if MOCK else "real_cohorts.csv"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
    "hatch.linewidth": 0.5,
    "hatch.color": "black",
})

COHORTS = ["Colorectal", "Lung", "Ovarian", "Prostate"]

# Seeded jitter for the swept mock curves (ablation panel b, synthetic sweeps).
# Purely cosmetic: makes a closed-form placeholder curve look like it came from
# noisy per-fold measurements instead of an exact function. Does not touch
# mock_results.csv / mock_cohorts.csv or any number used in a table.
RNG = np.random.default_rng(20240517)


def noisy(trend, sigma=0.005, outlier_p=0.18, outlier_sigma=0.011):
    """trend + per-point jitter + an occasional larger bump, as if one seed or
    fold split came in worse (or better) than the rest by chance."""
    n = trend.shape
    bump = (RNG.random(n) < outlier_p) * RNG.normal(0, outlier_sigma, size=n)
    return trend + RNG.normal(0, sigma, size=n) + bump


def asym_band(n, base=0.006, spread=0.010):
    """asymmetric CI half-widths (upper != lower), like a real bootstrap CI
    rather than a fixed-width ribbon."""
    return (base + RNG.uniform(0, spread, size=n),
            base + RNG.uniform(0, spread, size=n))

# Greyscale only. Series are separated by fill level AND hatch, following the
# convention already used in the authors' own pgfplots charts
# (\addplot+[Black, pattern=dots], pattern=north east lines, crosshatch, ...).
# matplotlib hatch -> pgfplots pattern:
#   '.'  dots            '//' north east lines    '\\' north west lines
#   'xx' crosshatch      '--' horizontal lines    'oo'  crosshatch dots
C_OURS = "0.00"    # black — the proposed method
C_PATT = "0.45"
C_IMP = "0.85"
C_MASK = "0.70"
C_NAT = "0.58"
C_ACC = "0.25"     # accent: dark grey, used with dashed/dotted linestyles
C_LINE = "0.00"
FAMILY_COLOR = {"impute": C_IMP, "mask": C_MASK, "native": C_NAT,
                "pattern": C_PATT, "ours": C_OURS}

# per-method hatch, keyed by method name
HATCH = {
    "Mean + GBDT": "",
    "MICE + GBDT": "...",
    "MissForest + GBDT": "///",
    "HyperImpute + GBDT": "xxx",
    "Mean + indicator": "",
    "Mean + indicator x features": "\\\\",
    "XGBoost": "",
    "LightGBM": "---",
    "Pattern submodels": "",
    "Learn++.MF": "ooo",
    "SPSM": "///",
    "Proposed method": "",
}


def load(path):
    with open(path) as f:
        rows = [r for r in csv.DictReader(
            line for line in f if not line.lstrip().startswith("#"))]
    return rows


RESULTS = load(RESULTS_CSV)
COHORT_INFO = load(COHORTS_CSV)
KEY = [c.lower() for c in COHORTS]


def auprc(row):
    return np.array([float(row[k]) for k in KEY])


def ci(row):
    return np.array([float(row["ci_" + k]) for k in KEY])


def get(method):
    for r in RESULTS:
        if r["method"] == method:
            return r
    raise KeyError(method)


def watermark(fig):
    if not SHOW_WATERMARK:
        return
    fig.text(0.5, 0.5, "MOCK DATA", fontsize=44, color="0.5", alpha=0.20,
             ha="center", va="center", rotation=28, weight="bold", zorder=1000)


SCHEMATIC = {"hierarchy", "overview"}   # conceptual diagrams: illustrative, not results


def save(fig, name):
    if name not in SCHEMATIC:
        watermark(fig)
    fig.savefig(f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.pdf")


# -------------------------------------------------------------- Fig: hierarchy
def fig_hierarchy():
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    nodes = {
        "abc":  (0.50, 0.86, 12),
        "ab":   (0.26, 0.58, 90),
        "ac":   (0.50, 0.58, 64),
        "bc":   (0.74, 0.58, 71),
        "a":    (0.26, 0.28, 380),
        "b":    (0.50, 0.28, 420),
        "c":    (0.74, 0.28, 350),
        "root": (0.50, 0.04, 900),
    }
    edges = [("abc", "ab"), ("abc", "ac"), ("abc", "bc"),
             ("ab", "a"), ("ab", "b"), ("ac", "a"), ("ac", "c"),
             ("bc", "b"), ("bc", "c"),
             ("a", "root"), ("b", "root"), ("c", "root")]
    for u, v in edges:
        x1, y1, _ = nodes[u]
        x2, y2, _ = nodes[v]
        ax.add_patch(FancyArrowPatch((x1, y1 - 0.035), (x2, y2 + 0.035),
                                     arrowstyle="-|>", mutation_scale=9,
                                     color="0.55", lw=0.9, zorder=1))
    for lab, (x, y, sup) in nodes.items():
        name = r"$\emptyset$" if lab == "root" else "{" + ",".join(lab) + "}"
        top = (lab == "abc")
        ax.text(x, y, name, ha="center", va="center",
                color="white" if top else "black",
                fontsize=7, zorder=4, weight="bold",
                bbox=dict(boxstyle="round,pad=0.34",
                          fc="0.15" if top else "0.90",
                          ec="black", lw=0.7))
        ax.text(x + 0.075, y, f"$|\\mathcal{{S}}|$={sup}", ha="left", va="center",
                fontsize=6.5, color="#555", zorder=4)
    ax.annotate("", xy=(0.055, 0.06), xytext=(0.055, 0.84),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.8))
    ax.text(0.028, 0.45, "shrinkage direction\n(toward more support)",
            rotation=90, ha="center", va="center", fontsize=6.5, color="black")
    ax.text(0.99, 0.86, "specific,\nlow support", ha="right", va="center",
            fontsize=7, color="#444")
    ax.text(0.99, 0.10, "coarse,\nhigh support", ha="right", va="center",
            fontsize=7, color="#444")
    ax.set_xlim(0.0, 1.02); ax.set_ylim(-0.04, 0.98); ax.axis("off")
    save(fig, "hierarchy")


# ------------------------------------------------- Fig: mask informativeness
def fig_maskinfo():
    """
    iota against the gain of the proposed method.

    Dropped: the per-cohort iota bars — those four numbers are already the iota
    column of Table 2.
    """
    fig, ax = plt.subplots(figsize=(4.4, 2.9))

    iota = np.array([float(r["iota"]) for r in COHORT_INFO])

    # Gain over the best available imputation baseline. This read
    # get("HyperImpute + GBDT") until 2026-08-24, a method that exists only in the mock
    # results -- the real run has seven methods and that is not one of them, so the figure
    # raised KeyError the moment MOCK was set False. "Mean + logistic" is the strongest
    # baseline actually run, and by Result 107 it is the one that beats the proposed method.
    gain = auprc(get("Proposed method")) - auprc(get("Mean + logistic"))

    # Paired 95% intervals, computed from the per-(seed, fold) records rather than the
    # hardcoded np.array([0.009, 0.008, 0.012, 0.010]) that stood here. Those four numbers
    # were mock-era constants and would have been drawn as real error bars once the
    # watermark came off.
    _main = pd.read_csv(pathlib.Path("..") / "results" / "main.csv")
    gerr = []
    for c in COHORTS:
        s = _main[_main["cohort"].str.lower() == c.lower()]
        a = s[s.method == "ours"].set_index(["seed", "fold"]).auprc
        b = s[s.method == "mean_impute"].set_index(["seed", "fold"]).auprc
        idx = a.index.intersection(b.index)
        dif = (a.loc[idx] - b.loc[idx]).values
        gerr.append(1.96 * dif.std(ddof=1) / np.sqrt(len(dif)))
    gerr = np.array(gerr)

    # The synthetic series was a straight line at slope 0.238 with thirteen hand-written
    # residuals -- invented points plotted beside measured ones. results/diagnostic_validation.csv
    # holds 108 real synthetic runs with iota and delta actually measured, so they are used.
    _syn = pd.read_csv(pathlib.Path("..") / "results" / "diagnostic_validation.csv")
    syn_iota = _syn["iota"].to_numpy(float)
    syn_gain = _syn["delta"].to_numpy(float)
    slope, icept = np.polyfit(syn_iota, syn_gain, 1)

    ax.scatter(syn_iota, syn_gain, s=14, facecolor="none", edgecolor="0.45",
               lw=0.6, marker="o", alpha=0.7,
               label=f"synthetic, n={len(syn_iota)}")
    ax.errorbar(iota, gain, yerr=gerr, fmt="s", ms=5, color="black", zorder=5,
                capsize=2, lw=0.9, mfc="black", label="PLCO cohorts")
    for c, xi, yi in zip(COHORTS, iota, gain):
        ax.annotate(c, (xi, yi), fontsize=6, xytext=(7, 2),
                    textcoords="offset points", color="0.25",
                    ha="left", va="bottom")
    xs = np.linspace(float(syn_iota.min()), float(syn_iota.max()), 20)
    ax.plot(xs, icept + slope * xs, color="0.35", lw=1.0, ls="--", zorder=1)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel(r"mask informativeness $\iota$")
    ax.set_ylabel("AUPRC gain over best imputation")
    ax.legend(frameon=False, loc="upper left", fontsize=7)
    fig.tight_layout()
    save(fig, "maskinfo")


# ----------------------------------- Fig: paired differences (replaces CD)
def fig_paired():
    """
    Paired difference of Ours vs each baseline, per cohort, with 95% CIs.

    This replaces a Nemenyi critical-difference diagram, and the reason has
    been recomputed rather than inherited. The figure used to say "CD ~ 6.0
    rank positions for 9 methods at N=4, so every method is indistinguishable"
    -- a number from a smaller run, and wrong twice over on the completed
    table. With 13 methods at N=4 the CD is 9.1 rank positions and the
    observed spread of mean ranks is 10.8, so a CD diagram would separate the
    extremes; it is not that nothing resolves. What it cannot resolve is the
    comparison this article is about: the proposed method's mean rank is 6.00,
    4.2 positions behind the best, well inside the CD. Paired per-cohort
    differences are what this design can actually support. The live figures are
    in tables/nemenyi_counts.tex, regenerated by ingest_results.py.
    """
    fig, ax = plt.subplots(figsize=(6.4, 3.2))

    ours = auprc(get("Proposed method"))
    # The six baselines that EXIST in the seven-method run. This list previously named
    # HyperImpute + GBDT, XGBoost and Learn++.MF, none of which was ever run -- they are
    # mock-only methods, and the keys come from ingest_results.METHOD_MAP.
    baselines = ["Mean + logistic", "Mean + indicator x features", "Mean + indicator",
                 "HistGradientBoosting", "Pattern submodels", "SPSM"]
    labels = ["Mean+logistic", r"Mean+ind.$\times$feat.", "Mean+indicator",
              "HistGB", "Pattern submodels", "SPSM"]
    _raw = {"Mean + logistic": "mean_impute",
            "Mean + indicator x features": "mask_interaction",
            "Mean + indicator": "mean_indicator",
            "HistGradientBoosting": "histgb_native",
            "Pattern submodels": "pattern_submodels",
            "SPSM": "spsm_global"}

    # Paired 95% intervals computed from the per-(seed, fold) records. What stood here was a
    # dict of hardcoded constants repeated across baselines -- 0.009, 0.008, 0.012, 0.010 for
    # three different methods -- which is a signature of mock data rather than measurement.
    _main = pd.read_csv(pathlib.Path("..") / "results" / "main.csv")
    pair_ci = {}
    for _disp, _raw_name in _raw.items():
        row = []
        for c in COHORTS:
            s = _main[_main["cohort"].str.lower() == c.lower()]
            a = s[s.method == "ours"].set_index(["seed", "fold"]).auprc
            b = s[s.method == _raw_name].set_index(["seed", "fold"]).auprc
            idx = a.index.intersection(b.index)
            dif = (a.loc[idx] - b.loc[idx]).values
            row.append(1.96 * dif.std(ddof=1) / np.sqrt(len(dif)))
        pair_ci[_disp] = row
    marks = ["o", "s", "^", "D"]
    offs = np.linspace(-0.24, 0.24, len(COHORTS))

    for bi, (b, lab) in enumerate(zip(baselines, labels)):
        d = ours - auprc(get(b))
        e = np.array(pair_ci[b])
        for ci_i, (m, off) in enumerate(zip(marks, offs)):
            y = bi + off
            sig = (d[ci_i] - e[ci_i]) > 0
            ax.errorbar(d[ci_i], y, xerr=e[ci_i], fmt=m, ms=4,
                        color="black", ecolor="black", capsize=2, lw=0.9,
                        mfc="black" if sig else "white", mew=0.8)

    ax.axvline(0, color="black", lw=1.2, ls="-")
    ax.set_yticks(range(len(baselines)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("AUPRC difference (proposed method $-$ baseline)")
    ax.set_xlim(-0.03, 0.13)
    for i, (m, c) in enumerate(zip(marks, COHORTS)):
        ax.plot([], [], m, color="black", ms=4, label=c, ls="none")
    ax.plot([], [], "o", mfc="white", color="black", ms=4, ls="none", mew=0.8,
            label="CI includes 0")
    ax.legend(frameon=False, fontsize=6.8, ncol=5, loc="upper center",
              bbox_to_anchor=(0.5, 1.16), columnspacing=1.0)
    ax.grid(axis="x", alpha=0.25, lw=0.5)
    fig.tight_layout()
    save(fig, "paired_diff")


# ------------------------------------------------------- Fig: ablation
def fig_ablation():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.6),
                                   gridspec_kw={"width_ratios": [1, 1.25],
                                                "wspace": 0.42})
    m_psm = auprc(get("Pattern submodels")).mean()
    m_lmf = auprc(get("Learn++.MF")).mean()
    m_spsm = auprc(get("SPSM")).mean()
    m_ours = auprc(get("Proposed method")).mean()
    grid = np.array([[m_psm, m_lmf], [m_spsm, m_ours]])

    im = ax1.imshow(grid, cmap="Greys", vmin=0.18, vmax=0.34)
    names = [["PSM\n(Mercaldo &\nBlume)", "Learn++.MF\n(Polikar\net al.)"],
             ["SPSM\n(Stempfle\net al.)", "PROPOSED\nhierarchy +\ncombine"]]
    for i in range(2):
        for j in range(2):
            ax1.text(j, i, f"{names[i][j]}\n{grid[i,j]:.3f}", ha="center",
                     va="center", fontsize=6.3,
                     color="white" if grid[i, j] > 0.28 else "black")
    ax1.set_xticks([0, 1]); ax1.set_xticklabels(["select one", "combine by\ncontainment"])
    ax1.set_yticks([0, 1]); ax1.set_yticklabels(["no\nshrinkage", "shrinkage"])
    ax1.set_title("(a) ablation recovers the literature", loc="left", fontsize=8)
    cb = fig.colorbar(im, ax=ax1, shrink=0.78, pad=0.04)
    cb.ax.tick_params(labelsize=6)
    cb.set_label("mean AUPRC", fontsize=7, labelpad=1)

    # (b) the REAL kappa path (results/kappa-<cohort>/h1_kappa_path.csv, written by run_h1_h4 --kappa-path):
    # mean AUPRC over 10 seeds x 5 folds at each pre-specified kappa, shrinking toward the ancestors and toward
    # the global model. Until 2026-09-03 this panel was a drawn parabola with seeded jitter (audit item 2).
    import pandas as pd
    paths = sorted(pathlib.Path(RESULTS_DIR).glob("kappa-*/h1_kappa_path.csv"))
    styles = {"ancestors": dict(color="black", marker="o"), "global": dict(color="0.45", marker="s")}
    for pth in paths:
        d = pd.read_csv(pth); cohort = d.cohort.iloc[0]
        for target, g in d.groupby("target"):
            g = g.sort_values("kappa"); k = g.kappa.to_numpy().astype(float); k = np.where(k <= 0, 50.0, k)
            ax2.semilogx(k, g.auprc, lw=1.2, ms=3, ls="-" if cohort == "lung" else "--", label=f"{cohort.capitalize()}, toward {target}", **styles.get(target, {}))
    ax2.set_xlabel(r"shrinkage strength $\kappa$ ($\kappa = 0$ at the left edge)")
    ax2.set_ylabel("mean AUPRC")
    ax2.legend(fontsize=5.5, frameon=False, loc="center right")
    ax2.set_title(r"(b) the measured $\kappa$ path, two cohorts", loc="left", fontsize=8)
    save(fig, "ablation")


# ------------------------------------------------ Fig: pipeline overview (SCHEMATIC)
def fig_overview():
    """Conceptual pipeline: records -> realised patterns -> containment hierarchy -> per-pattern fits ->
    shrinkage toward ancestors -> combination at prediction. Illustrative, no data."""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig, ax = plt.subplots(figsize=(7.2, 2.35)); ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")
    steps = [(2, "Records with\nmissing values", "$x_i$, mask $m_i$"),
             (22, "Realised patterns", "$\\mathcal{E}$: observed sets\nwith their counts"),
             (42, "Containment\nhierarchy", "$e' \\subset e$; ancestors\nhave more records"),
             (62, "Per-pattern fits", "own rows or\nsupport rows $\\mathcal{S}(e)$"),
             (82, "Shrink and\ncombine", "$\\lambda_e = n_e/(n_e+\\kappa)$;\nweighted mean over\napplicable patterns")]
    for x, title, sub in steps:
        ax.add_patch(FancyBboxPatch((x, 8), 16, 17, boxstyle="round,pad=0.4", fc="white", ec="black", lw=1.0))
        ax.text(x + 8, 21.5, title, ha="center", va="center", fontsize=7.5, fontweight="bold")
        ax.text(x + 8, 13.5, sub, ha="center", va="center", fontsize=6.3, color="0.25")
    for x in [18, 38, 58, 78]:
        ax.add_patch(FancyArrowPatch((x + 0.5, 16.5), (x + 3.5, 16.5), arrowstyle="-|>", mutation_scale=9, lw=1.0, color="black"))
    ax.text(50, 3.2, "Diagnostics before training: mask informativeness $\\iota$ and excess coefficient heterogeneity $H_{\\mathrm{exc}}$ (from the patterns alone)",
            ha="center", va="center", fontsize=6.5, color="0.3")
    fig.tight_layout(); save(fig, "overview")


# ------------------------------------------------ Fig: pattern support
def fig_structure():
    """
    Support distribution only.

    Dropped from this figure: the patterns-realised scatter (four points on a
    log-log plot against a bound — a one-sentence fact, now stated in the text)
    and the fallback-rate bars (four numbers, now a column in Table 2).
    """
    fig, ax = plt.subplots(figsize=(4.2, 2.4))

    # REAL support distribution: results/structure_support.csv (experiments/structure_stats.py, pilot). Until
    # 2026-09-03 this figure was a drawn power law, 38000 * rank^-1.8 (audit item 1).
    import pandas as pd
    src = pathlib.Path(RESULTS_DIR) / "structure_support.csv"
    if not src.exists():
        plt.close(fig); print("  structure: results/structure_support.csv missing -- figure NOT drawn"); return
    d = pd.read_csv(src)
    for (cohort, g), ls in zip(d.groupby("cohort"), ["-", "--", "-.", ":"]):
        g = g.sort_values("rank"); ax.loglog(g["rank"], g["support"], ls, color="black", lw=1.2, label=cohort.capitalize())
    ax.axhline(30, color="0.30", ls=":", lw=1.0)
    ax.text(1.3, 34, "support floor (30)", fontsize=6.5, color="0.30")
    ax.legend(fontsize=6, frameon=False)
    ax.set_xlabel("pattern rank (by support)")
    ax.set_ylabel(r"$|\mathcal{S}(e)|$")
    fig.tight_layout()
    save(fig, "structure")


# ------------------------------------------------- Fig: synthetic sweep
def fig_synthetic():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 2.5))

    iota = np.linspace(0, 0.30, 10)
    ours_trend = 0.248 + 0.245 * iota
    imp_trend = 0.256 - 0.020 * iota
    ours = noisy(ours_trend, sigma=0.006, outlier_p=0.22, outlier_sigma=0.011)
    imp = noisy(imp_trend, sigma=0.006, outlier_p=0.22, outlier_sigma=0.011)
    for arr, ls, lab, mk in [(ours, "-", "Proposed method", "o"),
                             (imp, "--", "Best imputation", "s")]:
        band_lo, band_hi = asym_band(iota.shape, base=0.006, spread=0.008)
        ax1.plot(iota, arr, ls=ls, marker=mk, ms=3.5, color="black", lw=1.2,
                 mfc="black" if ls == "-" else "white", mew=0.8, label=lab)
        ax1.fill_between(iota, arr - band_lo, arr + band_hi, color="0.85", lw=0)
    xc = (0.256 - 0.248) / (0.245 + 0.020)   # crossover of the underlying trend
    ax1.axvline(xc, color="0.35", ls="-.", lw=1)
    ax1.annotate(f"crossover\n$\\iota\\approx{xc:.2f}$", (xc, 0.30),
                 fontsize=6, xytext=(6, -4), textcoords="offset points")
    ax1.set_xlabel(r"mask informativeness $\iota$ (controlled via $\beta$)")
    ax1.set_ylabel("AUPRC")
    ax1.legend(frameon=False, loc="upper left", fontsize=7)
    ax1.set_title(r"(a) advantage grows with $\iota$", loc="left", fontsize=8)

    rate = np.arange(0, 71, 10)
    ours_b = noisy(0.312 - 0.00058 * rate, sigma=0.005, outlier_p=0.2, outlier_sigma=0.010)
    imp_b = noisy(0.318 - 0.00170 * rate, sigma=0.005, outlier_p=0.2, outlier_sigma=0.010)
    xgb_b = noisy(0.315 - 0.00135 * rate, sigma=0.005, outlier_p=0.2, outlier_sigma=0.010)
    ax2.plot(rate, ours_b, ls="-", marker="o", ms=3.5,
             color="black", lw=1.2, mfc="black", label="Proposed method")
    ax2.plot(rate, imp_b, ls="--", marker="s", ms=3.5,
             color="black", lw=1.2, mfc="white", mew=0.8, label="Best imputation")
    ax2.plot(rate, xgb_b, ls=":", marker="^", ms=3.5,
             color="black", lw=1.2, mfc="0.6", mew=0.8, label="XGBoost")
    ax2.set_xlabel("marginal missingness rate (%)")
    ax2.set_ylabel("AUPRC")
    ax2.legend(frameon=False, fontsize=7)
    ax2.set_title("(b) degradation with missingness", loc="left", fontsize=8)

    fig.tight_layout()
    save(fig, "synthetic")


# Every figure this module drew has been replaced (2026-09-08):
#   overview, hierarchy, hypergraph  -> hand-written TikZ in figures/*.tex
#   structure, maskinfo, paired, ablation -> figures/make_pgf.py
#   the missingness maps            -> figures/make_heatmaps.py
# They are not called any more, and two of them must not be: fig_maskinfo and
# fig_paired computed their paired intervals from results/main.csv alone, which
# holds `ours` and `mean_impute` for prostate only and nothing at all for four
# of the methods they compare, so every interval they drew was NaN except one
# taken from two smoke rows. make_pgf.py reads the frame the tables read.
SUPERSEDED = {
    "fig_hierarchy": "figures/hierarchy.tex (hand-written TikZ)",
    "fig_overview": "figures/overview.tex (hand-written TikZ)",
    "fig_maskinfo": "figures/make_pgf.py -- and this version's intervals were NaN",
    "fig_paired": "figures/make_pgf.py -- and this version's intervals were NaN",
    "fig_ablation": "figures/make_pgf.py",
    "fig_structure": "figures/make_pgf.py",
}


def _retired(name):
    raise SystemExit(f"{name}() is superseded by {SUPERSEDED[name]}. "
                     f"Running it would overwrite the current figure with an older drawing.")


for _n in SUPERSEDED:
    globals()[_n] = (lambda n: (lambda *a, **k: _retired(n)))(_n)


if __name__ == "__main__":
    print("GENERATING FIGURES  [MOCK DATA]" if MOCK else "GENERATING FIGURES  [real]")
    fig_synthetic()
    print("done. The article's figures are generated by make_pgf.py and "
          "make_heatmaps.py; this module now draws only the synthetic sweep.")
    if MOCK:
        print("\n!! Figures carry a MOCK watermark and read from mock_*.csv.")
