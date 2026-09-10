#!/usr/bin/env python3
"""The missingness map of each PLCO cohort, on the 40,000-record analysis sample.

Replaces figures/missing_heatmap_*.png, which were committed on 2026-07-19 --
five weeks before MOCK was set False and before real_cohorts.csv existed -- and
were never regenerated. Their dark-pixel fractions ranked the four cohorts
almost exactly opposite to the committed pct_miss under either polarity. See
HEATMAPS-STALE.md.

Three changes beyond being current:

  * Rows are ordered by missingness pattern, largest block first. The caption
    claims large groups of participants share an identical observed set; with
    rows in file order that claim is invisible, because identical patterns are
    scattered down the image. Sorted, each pattern is a band.
  * Columns are ordered by missingness rate, so the always-observed core is on
    the left and the tail on the right.
  * Rows are area-averaged into the output pixels rather than sampled, so a
    band's grey level is the missing fraction of the participants it covers
    and nothing is lost to aliasing.

Polarity is stated in the output: DARK IS MISSING.

Writes figures/missing_heatmap_<cohort>.png (data only, no text),
figures/missing_heatmaps.tex (the frame and every label, in document fonts) and
figures/heatmap_stats.csv (what the caption may quote).

Run on pilot, where the PLCO extraction lives:
    .venv/bin/python figures/make_heatmaps.py
"""
from __future__ import annotations

import csv
import os
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PAPER = HERE.parent
sys.path.insert(0, str(PAPER / "src"))

sys.path.insert(0, str(PAPER / "experiments"))

from hgmiss.data.plco import load_cohort           # noqa: E402
from run_h1_h4 import _subsample, FULL_MAX_N       # noqa: E402

_REPO = PAPER.parents[1]
ROOT = pathlib.Path(os.environ.get("PLCO_ROOT", _REPO / "datasets" / "plco"))
COHORTS = ["colorectal", "lung", "ovarian", "prostate"]

ROWS_PX = 320       # output rows per panel; participants are averaged into these
COL_PX = 8          # pixels drawn per variable
FLOOR = 0.06        # lightest grey a non-zero band gets, so a thin band is visible


def panel(mask):
    """A (ROWS_PX, d) array of missing fraction, rows by pattern, columns by rate."""
    miss = ~mask                                    # mask is True where observed
    order_c = np.argsort(miss.mean(axis=0), kind="stable")
    miss = miss[:, order_c]

    # group identical patterns, largest block first; np.unique sorts the rows so
    # identical patterns become adjacent, and the counts give the block sizes
    pats, inv, counts = np.unique(miss, axis=0, return_inverse=True, return_counts=True)
    rank = np.argsort(-counts, kind="stable")       # block index -> position
    pos = np.empty_like(rank)
    pos[rank] = np.arange(len(rank))
    order_r = np.argsort(pos[inv], kind="stable")
    miss = miss[order_r]

    n = miss.shape[0]
    edges = np.linspace(0, n, ROWS_PX + 1).astype(int)
    out = np.empty((ROWS_PX, miss.shape[1]), float)
    for i in range(ROWS_PX):
        a, b = edges[i], max(edges[i + 1], edges[i] + 1)
        out[i] = miss[a:b].mean(axis=0)
    return out, len(pats), int(counts.max()), n


def main() -> int:
    if not ROOT.exists():
        print(f"PLCO extraction not found at {ROOT}; run this on pilot", file=sys.stderr)
        return 1

    stats = []
    for c in COHORTS:
        co = load_cohort(c, ROOT)
        # the 40,000-record analysis sample, the same rows every table and every
        # other figure uses; on the full cohort the realised pattern count is
        # nearly three times Table S2's and the figure would contradict it
        X, _ = _subsample(co, seed=0, max_n=FULL_MAX_N)
        mask = ~np.isnan(np.asarray(X, float))
        grid, n_pat, biggest, n = panel(mask)

        # dark is missing; a band with any missingness never renders pure white
        shade = np.where(grid > 0, FLOOR + (1 - FLOOR) * grid, 0.0)
        img = Image.fromarray(((1 - shade) * 255).astype(np.uint8), mode="L")
        img = img.resize((grid.shape[1] * COL_PX, ROWS_PX), Image.NEAREST)
        img.save(HERE / f"missing_heatmap_{c}.png")

        pct = 100.0 * (~mask).mean()
        stats.append(dict(cohort=co.name.capitalize(), n=n, d=mask.shape[1],
                          pct_miss=round(pct, 2),
                          patterns=n_pat, largest_block=biggest,
                          largest_block_pct=round(100.0 * biggest / n, 2)))
        print(f"  {co.name:11} n={n:,} d={mask.shape[1]:3d} miss={pct:5.2f}% "
              f"patterns={n_pat:,} largest block={biggest:,} ({100*biggest/n:.1f}%)")

    with open(HERE / "heatmap_stats.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(stats[0]))
        w.writeheader()
        w.writerows(stats)

    _write_tex(stats)
    print(f"  wrote figures/missing_heatmaps.tex and heatmap_stats.csv")
    return 0


def _write_tex(stats):
    """The frame: every label in the document's own fonts, the data as a raster."""
    def num(v):
        return f"{v:,}".replace(",", "{,}")

    L = [f"% generated by figures/{pathlib.Path(__file__).name} -- do not edit; "
         f"edit the generator",
         r"\begin{tikzpicture}[y=1cm, x=1cm]"]
    for i, s in enumerate(stats):
        y = -i * 2.55
        key = s["cohort"].lower()
        L += [
            f"\\node[anchor=north west, inner sep=0pt] (p{i}) at (0,{y:.2f}) "
            f"{{\\includegraphics[width=12.4cm, height=1.95cm]"
            f"{{figures/missing_heatmap_{key}}}}};",
            f"\\draw[hggrey, line width=0.3pt] (p{i}.south west) rectangle (p{i}.north east);",
            f"\\node[anchor=south west, font=\\small\\bfseries] "
            f"at ([yshift=1.5pt]p{i}.north west) {{{s['cohort']}}};",
            f"\\node[anchor=south east, font=\\scriptsize, text=hgslate] "
            f"at ([yshift=1.5pt]p{i}.north east) "
            f"{{$d={s['d']}$, {s['pct_miss']:.1f}\\% missing, "
            f"{num(s['patterns'])} realised patterns, largest block "
            f"{num(s['largest_block'])} ({s['largest_block_pct']:.1f}\\%)}};",

        ]
    last = len(stats) - 1
    L += [
        # one two-line note: side by side the two ran into each other, the pair
        # being wider than the 12.4cm panel
        f"\\node[anchor=north west, font=\\scriptsize, text=hgslate, align=left] "
        f"at ([yshift=-0.28cm]p{last}.south west) "
        r"{variables ordered by missingness rate $\rightarrow$\\"
        r"participants ordered by pattern, largest block first};",
        r"\end{tikzpicture}",
        "",
    ]
    (HERE / "missing_heatmaps.tex").write_text("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
