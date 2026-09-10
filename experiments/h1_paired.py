"""H1 with a paired test, from the per-cell kappa files.

H1 says the interior of the kappa path beats both ends: the pattern submodel at kappa = 0 and the
single global model as kappa -> infinity. The article supports it from PATH MEANS, and says so as
a stated limitation, because until Result 140 the sweep wrote means and no cells. It now writes
cells, so the claim can be tested the way every other claim in the article is -- paired within
(seed, fold), median difference, Wilcoxon, against the 0.002 floor.

One asymmetry matters and is reported rather than smoothed over. kappa* = 10^4 was chosen as the
argmax of the path means on Lung and Colorectal. Testing at that kappa on those two cohorts reuses
the data that selected it, so the comparison is optimistic. On Ovarian and Prostate the same kappa
is a genuine out-of-sample choice, fixed in advance by the other cohorts, and those are the honest
tests of H1.

Usage: h1_paired.py [--kappa 10000]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

R = pathlib.Path(__file__).resolve().parent.parent / "results"
FLOOR = 0.002
SELECTED_ON = ("lung", "colorectal")     # kappa* was the argmax of these cohorts' path means


def _cells():
    """Every per-cell kappa file, tagged with where it came from."""
    out = []
    for f in sorted(R.rglob("h1_kappa_cells.csv")):
        d = pd.read_csv(f)
        d["_src"] = str(f.relative_to(R.parent))
        out.append(d)
    if not out:
        raise SystemExit("  no h1_kappa_cells.csv anywhere under results/")
    d = pd.concat(out, ignore_index=True)
    # the main table is the baseline feature set; the FULL-* directories hold the sensitivity runs
    if "feature_set" in d.columns:
        d = d[d.feature_set == "baseline"]
    # one run per cohort: prefer the most recently written file if a cohort appears twice
    keep = []
    for coh, g in d.groupby("cohort"):
        srcs = sorted(g._src.unique())
        if len(srcs) > 1:
            print(f"  {coh}: {len(srcs)} cell files, using {srcs[-1]}")
            g = g[g._src == srcs[-1]]
        keep.append(g)
    return pd.concat(keep, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kappa", type=float, default=10_000.0)
    a = ap.parse_args()
    d = _cells()

    print(f"\n  H1 paired, interior kappa = {a.kappa:,.0f} against each end of the path")
    print(f"  cohorts with cells: {sorted(d.cohort.unique())}\n")
    rows = []
    for (coh, tgt), g in d.groupby(["cohort", "target"]):
        piv = g.pivot_table(index=["seed", "fold"], columns="kappa", values="auprc")
        lo, hi = piv.columns.min(), piv.columns.max()
        if a.kappa not in piv.columns:
            print(f"  {coh}/{tgt}: kappa {a.kappa} not on the grid"); continue
        for end, name in ((lo, "kappa=0"), (hi, "kappa->inf")):
            v = (piv[a.kappa] - piv[end]).dropna().to_numpy(float)
            if len(v) < 10:
                continue
            med = float(np.median(v))
            pv = float(stats.wilcoxon(v).pvalue)
            rows.append(dict(cohort=coh, target=tgt, versus=name, n=len(v), median=med,
                             p=pv, x_floor=med / FLOOR,
                             clears=(abs(med) >= FLOOR and pv < 0.05),
                             out_of_sample=coh not in SELECTED_ON))
    res = pd.DataFrame(rows)

    # H1 as the article states it: the interior beats "the better limit", not merely one of them.
    # The better end is chosen from the PATH MEANS, as the article does, not per cell -- choosing
    # it per cell would pick the loser of each pair and inflate the margin.
    print("  H1 AS STATED: interior vs the BETTER end (end chosen from the path means)\n")
    strict = []
    for (coh, tgt), g in d.groupby(["cohort", "target"]):
        piv = g.pivot_table(index=["seed", "fold"], columns="kappa", values="auprc")
        lo, hi = piv.columns.min(), piv.columns.max()
        better = lo if piv[lo].mean() >= piv[hi].mean() else hi
        v = (piv[a.kappa] - piv[better]).dropna().to_numpy(float)
        med, pv = float(np.median(v)), float(stats.wilcoxon(v).pvalue)
        holds = med >= FLOOR and pv < 0.05
        strict.append(dict(cohort=coh, target=tgt, better_end=("kappa=0" if better == lo else "kappa->inf"),
                           median=med, p=pv, x_floor=med / FLOOR, h1_holds=holds,
                           out_of_sample=coh not in SELECTED_ON))
        tag = "out-of-sample" if coh not in SELECTED_ON else "kappa* chosen here"
        print(f"    {coh:11s} {tgt:10s} better end {('kappa=0' if better == lo else 'kappa->inf'):11s} "
              f"interior {med:+.6f}  p={pv:<9.3g} {med/FLOOR:5.2f}x  "
              f"{'H1 HOLDS' if holds else 'H1 NOT SUPPORTED':16s} [{tag}]")
    st = pd.DataFrame(strict)
    st.to_csv(R / "h1_strict.csv", index=False)
    print(f"\n  wrote {R / 'h1_strict.csv'}")
    # Emit the table AND the counts the prose depends on. A prose sentence saying "one of three"
    # goes stale the moment a fourth cohort lands, and a stale count reads as a finding rather
    # than as an oversight. Both come from here, so they cannot disagree with each other.
    _NAME = {"lung": "Lung", "colorectal": "Colorectal", "ovarian": "Ovarian",
             "prostate": "Prostate"}
    _END = {"kappa=0": r"$\kappa=0$", "kappa->inf": r"$\kappa\to\infty$"}
    tex = pathlib.Path(__file__).resolve().parent.parent / "tables" / "h1_paired.tex"
    lines = [r"% GENERATED by experiments/h1_paired.py -- do not edit by hand.",
             r"\begin{tabular}{@{}llrrrl@{}}", r"\toprule",
             r"Cohort & Target & Interior $-$ better end & $p$ & $\times$ floor & Better end \\",
             r"\midrule"]
    for tgt in ("ancestors", "global"):
        for _, r in st[st.target == tgt].sort_values("cohort").iterrows():
            pv = f"${r.p:.3g}$".replace("e-0", r"\times10^{-").replace("e-", r"\times10^{-")
            if r"\times10" in pv:
                pv = pv[:-1] + "}$"
            lines.append(f"{_NAME.get(r.cohort, r.cohort)} & {r.target} & ${r['median']:+.6f}$ & "
                         f"{pv} & ${r.x_floor:.2f}$ & {_END[r.better_end]} \\\\")
        if tgt == "ancestors":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    tex.write_text("\n".join(lines) + "\n")
    print(f"  wrote {tex}")

    _anc = st[st.target == "ancestors"]

    # Where each cohort's ancestor-target path peaks, as prose. Hardcoding this sentence would
    # make it wrong the moment another cohort lands, and a wrong sentence about which cohorts
    # agree reads as a finding rather than as an oversight.
    _pk = {}
    for coh, g in d[d.target == "ancestors"].groupby("cohort"):
        piv = g.pivot_table(index=["seed", "fold"], columns="kappa", values="auprc")
        lo, hi = piv.columns.min(), piv.columns.max()
        _pk[coh] = piv.mean()[[k for k in piv.columns if k not in (lo, hi)]].idxmax()
    _grp = {}
    for coh, k in _pk.items():
        _grp.setdefault(k, []).append(_NAME.get(coh, coh))
    _parts = []
    for k in sorted(_grp, key=lambda z: -len(_grp[z])):
        names = sorted(_grp[k])
        who = names[0] if len(names) == 1 else " and ".join([", ".join(names[:-1]), names[-1]])
        exp = int(round(np.log10(k)))
        ktex = f"10^{{{exp}}}" if abs(k - 10 ** exp) < 1e-9 else f"{k/10**exp:.0f}\\times10^{{{exp}}}"
        _parts.append(f"{who} at $\\kappa = {ktex}$")
    _peaks = "; ".join(_parts)

    # Split the ancestor-target result by whether kappa* was chosen on that cohort. This is the
    # finding, not the total: the count alone reads as "it holds on half of them", which is true
    # and hides that the half is exactly the half that picked the parameter.
    _oos = _anc[_anc.out_of_sample]
    _sel = _anc[~_anc.out_of_sample]
    _n_oos, _n_oos_clear = len(_oos), int(_oos.h1_holds.sum())
    _n_sel, _n_sel_clear = len(_sel), int(_sel.h1_holds.sum())

    macros = tex.parent / "h1_counts.tex"
    macros.write_text(
        "% GENERATED by experiments/h1_paired.py -- do not edit by hand.\n"
        f"\\newcommand{{\\HOneCohorts}}{{{len(_anc)}}}\n"
        f"\\newcommand{{\\HOneClears}}{{{int(_anc.h1_holds.sum())}}}\n"
        f"\\newcommand{{\\HOneCombos}}{{{len(st)}}}\n"
        f"\\newcommand{{\\HOneCombosClear}}{{{int(st.h1_holds.sum())}}}\n"
        f"\\newcommand{{\\HOneKappa}}{{{a.kappa:,.0f}}}\n"
        f"\\newcommand{{\\HOnePeaks}}{{{_peaks}}}\n"
        f"\\newcommand{{\\HOneOOS}}{{{_n_oos}}}\n"
        f"\\newcommand{{\\HOneOOSClears}}{{{_n_oos_clear}}}\n"
        f"\\newcommand{{\\HOneSel}}{{{_n_sel}}}\n"
        f"\\newcommand{{\\HOneSelClears}}{{{_n_sel_clear}}}\n")
    print(f"  wrote {macros}")

    anc = st[st.target == "ancestors"]
    print(f"  ancestor target: H1 holds on {int(anc.h1_holds.sum())} of {len(anc)} cohorts "
          f"({int(anc[anc.out_of_sample].h1_holds.sum())} of {int(anc.out_of_sample.sum())} out-of-sample)")

    for tgt, g in res.groupby("target"):
        print(f"  target = {tgt}")
        for _, r in g.sort_values(["out_of_sample", "cohort"]).iterrows():
            tag = "out-of-sample" if r.out_of_sample else "kappa* chosen here"
            print(f"    {r.cohort:11s} vs {r.versus:11s} median {r['median']:+.6f} "
                  f"p={r.p:<9.3g} {r.x_floor:5.2f}x floor  "
                  f"{'CLEARS' if r.clears else 'below floor' if r.p < 0.05 else 'n.s.':12s} [{tag}]")
        print()
    out = R / "h1_paired.csv"
    res.to_csv(out, index=False)
    print(f"  wrote {out}")
    oos = res[res.out_of_sample & (res.target == "ancestors")]
    if len(oos):
        print(f"\n  OUT-OF-SAMPLE ANCESTOR TESTS: {int(oos.clears.sum())} of {len(oos)} clear the floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
