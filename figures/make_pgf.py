#!/usr/bin/env python3
"""pgfplots sources for Paper 1's data figures.

Replaces the matplotlib versions of structure, maskinfo, paired_diff and
ablation.  Reads the same committed CSVs as before through make_figures'
helpers, so no number is restated here; only the drawing changes.

Run:  python make_pgf.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# papers/common/, found by searching upward: a fixed hop count is right in the
# monorepo and wrong in an extracted release
for _d in [pathlib.Path(__file__).resolve(), *pathlib.Path(__file__).resolve().parents]:
    if (_d / "common" / "pgfemit.py").exists():
        sys.path.insert(0, str(_d / "common")); break
else:
    raise SystemExit("could not find common/pgfemit.py above " + __file__)

from pgfemit import Fig, declutter, fmt                     # noqa: E402
from make_figures import (COHORTS, COHORT_INFO, RESULTS_DIR,  # noqa: E402
                          auprc, get)
from ingest_results import load_main_frame                  # noqa: E402

RESULTS = HERE.parent / "results"
SERIES = ["hg s1", "hg s2", "hg s3", "hg s4"]      # one per cohort, in COHORTS order

# The per-fold frame, read the way the tables read it. The figures used to open
# results/main.csv alone; of the methods they compare, that file holds `ours`
# and `mean_impute` for prostate only, two rows each, and both are smoke output
# at subsample_n=1,500 which load_main_frame drops. Every interval the figures
# drew was therefore NaN and silently omitted, except one drawn from two smoke
# rows.
MAIN = load_main_frame(RESULTS)
MAIN = MAIN[MAIN.feature_set == "baseline"]
MIN_PAIRS = 10          # the rule build_spsm_pairs applies to the same comparison


def paired(comparator):
    """Mean paired difference of `ours` against one comparator, per cohort.

    Returns (mean difference, half-width of the 95% interval, pair count) with
    NaN where a cohort has fewer than MIN_PAIRS complete pairs, so a thin
    comparison is visibly absent rather than drawn as a point estimate.
    """
    m, e, n = [], [], []
    for c in COHORTS:
        piv = (MAIN[MAIN.cohort.str.lower() == c.lower()]
               .pivot_table(index=["seed", "fold"], columns="method", values="auprc"))
        if not {"ours", comparator} <= set(piv.columns):
            m.append(np.nan); e.append(np.nan); n.append(0); continue
        pair = piv[["ours", comparator]].dropna()
        d = (pair["ours"] - pair[comparator]).to_numpy(float)
        if len(d) < MIN_PAIRS:
            m.append(np.nan); e.append(np.nan); n.append(len(d)); continue
        m.append(d.mean())
        e.append(1.96 * d.std(ddof=1) / np.sqrt(len(d)))
        n.append(len(d))
    return np.array(m), np.array(e), np.array(n)


def _write(fig, name):
    (HERE / f"{name}.tex").write_text(fig.render(__file__))
    print(f"  wrote figures/{name}.tex")


# --------------------------------------------------------------- structure
def fig_structure():
    """The support distribution, one curve per cohort."""
    src = RESULTS_DIR / "structure_support.csv"
    if not src.exists():
        print("  structure: results/structure_support.csv missing -- not drawn")
        return
    d = pd.read_csv(src)

    fig = Fig()
    ax = fig.axis(
        "S", "hg axis, hg legend below",
        width=r"0.62\textwidth", height="5.6cm",
        xmode="log", ymode="log",
        xlabel="pattern rank (by support)", ylabel=r"$|\mathcal{S}(e)|$",
        legend_style=("font=\\scriptsize, draw=none, fill=none, "
                      "at={(0.5,-0.26)}, anchor=north, legend columns=4, "
                      "column sep=1.2em"))
    ax.raw(r"\addplot[hg rule, forget plot, domain=1:10000] {30};")
    ax.raw(r"\node[font=\scriptsize, text=hggrey, anchor=south west] "
           r"at (axis cs:1.15,33) {support floor (30)};")
    for (cohort, g), style in zip(d.groupby("cohort"), SERIES):
        g = g.sort_values("rank")
        ax.plot(f"{style}, mark=none, line width=1.0pt",
                g["rank"], g["support"], digits=6, legend=cohort.capitalize())
    _write(fig, "structure")


# --------------------------------------------------------------- maskinfo
def fig_maskinfo():
    """Mask informativeness against the gain, synthetic runs and the cohorts."""
    iota = np.array([float(r["iota"]) for r in COHORT_INFO])
    gain, gerr, npair = paired("mean_impute")
    published = auprc(get("Proposed method")) - auprc(get("Mean + logistic"))
    # the paired mean must reproduce the difference of the published means
    if not np.allclose(gain, published, atol=2e-4):
        raise SystemExit(f"paired means {gain} disagree with the published "
                         f"difference {published}; do not draw the figure")

    syn = pd.read_csv(RESULTS / "diagnostic_validation.csv")
    si, sg = syn["iota"].to_numpy(float), syn["delta"].to_numpy(float)
    slope, icept = np.polyfit(si, sg, 1)

    xlo, xhi = si.min() - 0.02, max(si.max(), iota.max()) + 0.03
    ylo = min(sg.min(), (gain - gerr).min()) - 0.012
    yhi = max(sg.max(), (gain + gerr).max()) + 0.012

    fig = Fig()
    ax = fig.axis(
        "M", "hg axis, hg legend in, hg decimal x=2, hg decimal y=2",
        width=r"0.68\textwidth", height="6.0cm", scale_only_axis=True, clip=False,
        xlabel=r"mask informativeness $\iota$",
        ylabel="AUPRC gain over the best imputation",
        xmin=fmt(xlo, 4), xmax=fmt(xhi, 4), ymin=fmt(ylo, 4), ymax=fmt(yhi, 4),
        enlarge_x_limits=False, enlarge_y_limits=False)
    ax.raw(f"\\draw[hg rule] (axis cs:{fmt(xlo,4)},0) -- (axis cs:{fmt(xhi,4)},0);")
    ax.plot("hggrey, only marks, mark=o, mark size=1.4pt, "
            "mark options={line width=0.5pt}", si, sg, digits=5,
            legend=f"synthetic, $n={len(si)}$")
    xs = [xlo, xhi]
    ax.plot("hgslate, dashed, mark=none, line width=0.9pt",
            xs, [icept + slope * x for x in xs], digits=5,
            legend=f"least squares on the synthetic runs (slope ${slope:+.2f}$)")
    ax.plot("hg s2, only marks, mark size=2.6pt", iota, gain, yerr=gerr, digits=5,
            legend="PLCO cohorts, with paired 95\\% intervals")

    # 0.68\textwidth by 6.0cm, as a scale-only-axis box
    lab = [(float(x), float(y), c) for x, y, c in zip(iota, gain, COHORTS)]
    for (x, y, c), (anchor, dx, dy) in zip(
            lab, declutter(lab, (xlo, xhi), (ylo, yhi), box=(307, 170),
                           font_pt=6.0, radius=11.0)):
        ax.raw(f"\\node[font=\\tiny, text=hgred, anchor={anchor}, "
               f"xshift={dx}pt, yshift={dy}pt] at (axis cs:{fmt(x,5)},{fmt(y,5)}) "
               f"{{{c}}};")
    _write(fig, "maskinfo")


# ------------------------------------------------------------- paired_diff
def fig_paired():
    """Paired difference against each baseline, per cohort, with 95% intervals."""
    ours = auprc(get("Proposed method"))
    baselines = ["Mean + logistic", "Mean + indicator x features", "Mean + indicator",
                 "HistGradientBoosting", "Pattern submodels", "SPSM"]
    labels = ["Mean\\,+\\,logistic", r"Mean\,+\,ind.$\times$feat.", "Mean\\,+\\,indicator",
              "HistGB", "Pattern submodels", "SPSM"]
    raw = {"Mean + logistic": "mean_impute",
           "Mean + indicator x features": "mask_interaction",
           "Mean + indicator": "mean_indicator",
           "HistGradientBoosting": "histgb_native",
           "Pattern submodels": "pattern_submodels",
           "SPSM": "spsm_global"}

    diffs, ci = {}, {}
    for disp, name in raw.items():
        diffs[disp], ci[disp], _ = paired(name)
        published = ours - auprc(get(disp))
        if not np.allclose(diffs[disp], published, atol=2e-4):
            raise SystemExit(f"{disp}: paired means {diffs[disp]} disagree with the "
                             f"published difference {published}; do not draw the figure")
    # The axis ran to +0.13 while nothing reached +0.04, so every point sat in
    # the leftmost quarter of the panel. Take the limits from the data.
    lo = min((diffs[b] - ci[b]).min() for b in baselines)
    hi = max((diffs[b] + ci[b]).max() for b in baselines)
    pad = 0.06 * (hi - lo)

    offs = np.linspace(-0.26, 0.26, len(COHORTS))
    fig = Fig()
    ax = fig.axis(
        "P", "hg axis, hg xgrid, hg decimal x=2",
        width=r"0.80\textwidth", height="6.2cm",
        xlabel="AUPRC difference (proposed method $-$ baseline)",
        xmin=fmt(lo - pad, 4), xmax=fmt(hi + pad, 4), enlarge_x_limits=False,
        xtick=",".join(fmt(v, 3) for v in np.arange(
            np.ceil((lo - pad) * 100) / 100, (hi + pad) + 1e-9, 0.01)),
        ymin=-0.6, ymax=len(baselines) - 0.4, enlarge_y_limits=False, y_dir="reverse",
        ytick=",".join(str(i) for i in range(len(baselines))),
        yticklabels=",".join("{%s}" % s for s in labels),
        y_tick_label_style="font=\\small, align=right",
        legend_style=("font=\\scriptsize, draw=none, fill=none, "
                      "at={(0.5,-0.26)}, anchor=north, legend columns=5, "
                      "column sep=1.1em"))
    ax.raw(f"\\draw[hgslate, line width=0.7pt] (axis cs:0,-0.6) -- "
           f"(axis cs:0,{len(baselines) - 0.4});")

    # A filled marker is a difference whose interval clears zero; the shape
    # names the cohort. The old legend mixed the two into one row of glyphs.
    for ci_i, (c, style, off) in enumerate(zip(COHORTS, SERIES, offs)):
        xs = [float(diffs[b][ci_i]) for b in baselines]
        es = [float(ci[b][ci_i]) for b in baselines]
        ys = [i + off for i in range(len(baselines))]
        sig = [x - e > 0 for x, e in zip(xs, es)]
        ax.plot(f"{style}, only marks", [x for x, s in zip(xs, sig) if s],
                [y for y, s in zip(ys, sig) if s],
                xerr=[e for e, s in zip(es, sig) if s], digits=5, legend=c)
        rest = [(x, y, e) for x, y, e, s in zip(xs, ys, es, sig) if not s]
        if rest:
            ax.plot(f"{style}, only marks, mark options={{fill=white, "
                    f"line width=0.7pt}}", [r[0] for r in rest], [r[1] for r in rest],
                    xerr=[r[2] for r in rest], digits=5, forget=True)
    ax.raw(r"\addlegendimage{hgslate, only marks, mark=*, mark size=1.9pt, "
           r"mark options={fill=white, draw=hgslate, line width=0.7pt}}")
    ax.raw(r"\addlegendentry{interval includes zero}")
    _write(fig, "paired_diff")


# --------------------------------------------------------------- ablation
def fig_ablation():
    """The 2x2 ablation, and the measured shrinkage path."""
    cells = [[("PSM", "Fletcher Mercaldo \\& Blume", auprc(get("Pattern submodels")).mean()),
              ("Learn++.MF", "Polikar et al.", auprc(get("Learn++.MF")).mean())],
             [("SPSM", "Stempfle et al.", auprc(get("SPSM")).mean()),
              ("proposed", "hierarchy $+$ combine", auprc(get("Proposed method")).mean())]]

    fig = Fig()
    # Panel A was an imshow on a 0.18-0.34 colour scale. All four values are
    # near 0.136, below the scale's floor, so every cell rendered white and the
    # colourbar beside them meant nothing. Four numbers that agree to three
    # decimals are a table, not a heatmap, so the grid now just states them.
    fig.raw(r"\node[anchor=north west, font=\small] (Atitle) at (0,0) "
            r"{\textbf{A}\quad The ablation recovers the literature};", after=False)
    for i, (row, ylab) in enumerate(zip(cells, ["no shrinkage", "shrinkage"])):
        for j, (name, who, val) in enumerate(row):
            best = (i, j) == (1, 1)
            sty = "hg accent" if best else "hg box"
            fig.raw(f"\\node[{sty}, text width=2.85cm, align=center, minimum height=1.5cm, "
                    f"anchor=north west, font=\\scriptsize, inner sep=3pt] "
                    f"(c{i}{j}) at ({1.85 + j * 3.20:.2f},{-0.55 - i * 1.7:.2f}) "
                    f"{{{{\\footnotesize\\bfseries {name}}}\\\\[1pt]"
                    f"{{\\tiny\\color{{hgslate}} {who}}}\\\\[2pt]"
                    f"AUPRC ${val:.3f}$}};", after=False)
        fig.raw(f"\\node[font=\\small, anchor=east, align=right] "
                f"at (1.72,{-1.30 - i * 1.7:.2f}) {{{ylab}}};", after=False)
    for j, xlab in enumerate(["select one", "combine by\\\\containment"]):
        fig.raw(f"\\node[font=\\small, anchor=north, align=center] "
                f"at ({3.30 + j * 3.20:.2f},-3.95) {{{xlab}}};", after=False)

    paths = sorted(pathlib.Path(RESULTS_DIR).glob("kappa-*/h1_kappa_path.csv"))
    ax = fig.axis(
        "K", "hg axis, hg legend below, hg decimal y=3",
        at="($(c01.north east)+(2.0cm,0.70cm)$)", anchor="north west",
        width=r"0.40\textwidth", height="4.6cm", xmode="log",
        xlabel=r"shrinkage strength $\kappa$ ($\kappa=0$ at the left edge)",
        ylabel="mean AUPRC",
        title=r"\textbf{B}\quad The measured $\kappa$ path",
        legend_style=("font=\\scriptsize, draw=none, fill=none, "
                      "at={(0.5,-0.38)}, anchor=north, legend columns=2, "
                      "column sep=1.0em, row sep=0.5pt"))
    style = {"ancestors": "hg s1", "global": "hg s2"}
    for pth in paths:
        d = pd.read_csv(pth)
        cohort = d.cohort.iloc[0]
        for target, g in d.groupby("target"):
            g = g.sort_values("kappa")
            k = np.where(g.kappa.to_numpy(float) <= 0, 50.0, g.kappa.to_numpy(float))
            dash = "" if cohort == "lung" else ", dashed"
            ax.plot(f"{style.get(target, 'hg s6')}{dash}, mark size=1.4pt, line width=0.9pt",
                    k, g.auprc, digits=5,
                    legend=f"{cohort.capitalize()}, toward {target}")
    _write(fig, "ablation")



# -------------------------------------------------------------- hexc_lens
def fig_hexc_lens():
    """What H_exc summarises, pattern by pattern, on the four cohorts and MIMIC-IV.

    Reads figures/hexc_lens.csv, which hexc_lens.py commits. That file spells the
    permuted arm "null" in its kind column, and pandas parses the literal string
    null as NaN, so a default read silently discards exactly half the rows --
    the whole permuted cloud. Hence keep_default_na=False, and a count check.
    """
    src, ssrc = HERE / "hexc_lens.csv", HERE / "hexc_lens_summary.csv"
    if not src.exists() or not ssrc.exists():
        print("  hexc_lens: figures/hexc_lens*.csv missing -- not drawn")
        return
    d = pd.read_csv(src, keep_default_na=False)
    d["support"] = d["support"].astype(float)
    d["divergence"] = d["divergence"].astype(float)
    s = pd.read_csv(ssrc).set_index("cohort")
    kinds = set(d.kind.unique())
    if kinds != {"real", "null"}:
        raise SystemExit(f"hexc_lens.csv has kinds {kinds}; expected real and null")
    for c, g in d.groupby("cohort"):
        n = g.kind.value_counts()
        if n.get("real", 0) != n.get("null", 0):
            raise SystemExit(f"{c}: {n.get('real', 0)} real rows against "
                             f"{n.get('null', 0)} permuted; do not draw the figure")

    order = [c for c in ["colorectal", "lung", "ovarian", "prostate", "mimic4"]
             if c in set(d.cohort)]
    nice = {"mimic4": "MIMIC-IV"}
    ylo, yhi = d.divergence.min() - 0.12, d.divergence.max() + 0.12

    fig = Fig()
    prev = None
    for i, c in enumerate(order):
        g = d[d.cohort == c]
        first_in_row = i % 3 == 0
        opts = dict(width=r"0.245\textwidth", height="3.5cm", scale_only_axis=True,
                    xmode="log", ymin=fmt(ylo, 3), ymax=fmt(yhi, 3),
                    enlarge_y_limits=False,
                    xlabel=r"pattern support $|\mathcal{S}(e)|$",
                    title=("\\textbf{%s}\\quad %s, $H_{\\mathrm{exc}}=%+.3f$"
                           % (chr(65 + i), nice.get(c, c.capitalize()),
                              s.loc[c, "H_exc_mean"])))
        if first_in_row:
            opts["ylabel"] = "divergence from pooled"
        else:
            opts["yticklabels"] = "\\empty"
        if i == 0:
            ax = fig.axis("p0", "hg axis, hg decimal y=1", **opts)
        elif first_in_row:
            ax = fig.axis(f"p{i}", "hg axis, hg decimal y=1",
                          at="($(p0.south west)-(0,%.2fcm)$)" % (2.35 * (i // 3)),
                          anchor="north west", **opts)
        else:
            ax = fig.right_of(f"p{i}", "hg axis, hg decimal y=1", prev,
                              gap="0.95cm", **opts)
        prev = f"p{i}"

        for kind, style in (("null", "hggrey, only marks, mark=*, mark size=1.3pt, "
                                     "mark options={draw=none, fill=hggrey, fill opacity=0.75}"),
                            ("real", "hgred, only marks, mark=*, mark size=1.3pt, "
                                     "mark options={draw=none, fill=hgred, fill opacity=0.85}")):
            gg = g[g.kind == kind]
            ax.plot(style, gg.support, gg.divergence, digits=5, forget=True)
        # the support-weighted means, whose difference is H_exc
        for kind, colour, dash in (("null", "hggrey", ", dashed"), ("real", "hgred", "")):
            gg = g[g.kind == kind]
            h = float((gg.support * gg.divergence).sum() / gg.support.sum())
            ax.raw("\\addplot[%s%s, line width=0.8pt, mark=none, forget plot] "
                   "coordinates {(%.0f,%s) (%.0f,%s)};"
                   % (colour, dash, gg.support.min() * 0.7, fmt(h, 5),
                      gg.support.max() * 1.4, fmt(h, 5)))

    # one legend for the figure, in the space the fifth panel leaves free
    fig.raw("\\node[anchor=north west, font=\\scriptsize, align=left, text=hgslate] "
            "at ($(p3.north east)+(2.6cm,0)$) "
            "{\\tikz{\\fill[hgred] (0,0) circle (1.6pt);}~real mask\\\\[3pt]"
            "\\tikz{\\fill[hggrey] (0,0) circle (1.6pt);}~row-permuted mask\\\\[3pt]"
            "the rules are the support-weighted\\\\means, and $H_{\\mathrm{exc}}$ is "
            "their difference};")
    _write(fig, "hexc_lens")


if __name__ == "__main__":
    fig_structure()
    fig_maskinfo()
    fig_paired()
    fig_ablation()
    fig_hexc_lens()
