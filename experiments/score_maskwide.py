"""Score MASKWIDE against prereg/MASKWIDE.md.

Committed before any result file exists. The null is read first and sets the floor at each schema
width, because LOWQ's registered lesson is that a fixed +0.002 threshold sits below this
estimator's own noise at a narrow schema.
"""
from __future__ import annotations

import glob
import pathlib
import sys

import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1] / "results" / "maskwide"
PROTOCOL = {"cand_eicu_regime", "cand_mimic4_regime", "cand_nhanes", "sweep_42739"}
PRIMARY = ("family_cv", "mean_indicator")


def primary(d: pd.DataFrame) -> pd.DataFrame:
    """family_cv - mean_indicator, paired within (dataset, q, draw, fold), then averaged."""
    w = d.pivot_table(index=["dataset", "q", "draw", "fold", "permuted"],
                      columns="arm", values="auprc").reset_index()
    if not set(PRIMARY) <= set(w.columns):
        sys.exit("missing arms; nothing to score, which is NOT a pass")
    w["gain"] = w[PRIMARY[0]] - w[PRIMARY[1]]
    return w.groupby(["dataset", "q", "draw", "permuted"]).gain.mean().reset_index()


def main() -> int:
    fs = sorted(glob.glob(str(R / "*.csv")))
    if not fs:
        print(f"no results in {R} -- nothing to score, which is NOT a pass")
        return 2
    d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    g = primary(d)
    real, null = g[g.permuted < 0], g[g.permuted >= 0]
    qs = sorted(g.q.unique(), reverse=True)
    print(f"{len(fs)} files; {real.dataset.nunique()} datasets real, "
          f"{null.dataset.nunique()} with a null; q = {qs}\n")

    # ---- the null first, per prereg -------------------------------------------------
    floor = {q: float(np.percentile(null[null.q == q].gain, 95)) if len(null[null.q == q]) else np.nan
             for q in qs}
    print("permuted floor (95th percentile of the null primary) by schema width")
    for q in qs:
        s = null[null.q == q].gain
        print(f"   q={q:<5} floor {floor[q]:+.4f}   n={len(s):>3}  median {s.median():+.4f}" if len(s)
              else f"   q={q:<5} NO NULL RUNS")
    print()

    rp = real.groupby(["dataset", "q"]).gain.mean().unstack("q")
    print("real primary, family_cv - mean_indicator, by dataset and width")
    print(rp.reindex(columns=qs).round(4).to_string(), "\n")

    checks = {}
    hi, lo = min(qs), max(qs)                      # hi = narrowest schema (0.1), lo = full (1.0)
    if lo in rp.columns:
        checks["N1 at q=1.0 the primary is within +/-0.002 of zero on >=14/17"] = \
            bool((rp[lo].abs() <= 0.002).sum() >= 14)
    if not np.isnan(floor.get(hi, np.nan)) and not np.isnan(floor.get(lo, np.nan)):
        checks["N2 the floor is finite everywhere and larger at q=0.1 than at q=1.0"] = \
            bool(floor[hi] > floor[lo])
    if hi in rp.columns:
        above = rp[hi] > floor[hi]
        checks[f"P1 at q=0.1 the real primary exceeds the floor ({floor[hi]:+.4f}) on >=9/17"] = \
            bool(above.sum() >= 9)
        if lo in rp.columns:
            checks["P2 the primary is larger at q=0.1 than at q=1.0 on >=12/17"] = \
                bool((rp[hi] > rp[lo]).sum() >= 12)
        prot = [x for x in rp.index if x in PROTOCOL]
        checks["P3 on the four protocol-driven datasets it exceeds the floor on >=3/4"] = \
            bool(sum(rp.loc[x, hi] > floor[hi] for x in prot) >= 3)
        print(f"datasets above the q=0.1 floor: {int(above.sum())} of {len(above)} "
              f"-> {sorted(rp.index[above])}\n")

    # ---- secondary analysis S1/S2, registered before scoring -------------------------
    import numpy as _np
    from scipy import stats as _st
    PATTERNS = {"cand_eicu_regime": 35188, "cand_mimic4_regime": 9448, "cand_acs_income": 1723,
                "sweep_42093": 1256, "sweep_42739": 986, "sweep_42333": 782, "cand_nhanes": 593,
                "cand_porto": 82, "sweep_42737": 38, "sweep_42136": 35, "cand_airbnb": 33,
                "sweep_46725": 24, "sweep_42080": 19, "sweep_41275": 17, "sweep_46703": 7,
                "cand_higgs": 6, "sweep_46654": 5}
    print("secondary: primary quantity against log10(realised patterns)")
    for tag, qq in (("S1", lo), ("S2", hi)):
        if qq not in rp.columns:
            continue
        ds = [d for d in rp.index if d in PATTERNS]
        x = _np.log10([PATTERNS[d] for d in ds]); yv = rp.loc[ds, qq].to_numpy(float)
        ok = ~_np.isnan(yv)
        rho, pv = _st.spearmanr(x[ok], yv[ok])
        print(f"   q={qq:<5} rho {rho:+.3f}  p={pv:.3g}  n={int(ok.sum())}")
        checks[f"{tag} primary vs log10(patterns) at q={qq}: rho <= -0.4"] = bool(rho <= -0.4)
    print()

    for k, v in checks.items():
        print(("  HELD    " if v else "  FAILED  ") + k)
    print()
    instrument = [k for k in checks if k.startswith(("N1", "N2"))]
    if any(not checks[k] for k in instrument):
        print("INSTRUMENT FAILED -- per prereg/MASKWIDE.md nothing is claimed from this run.")
        return 1
    bad = [k for k, v in checks.items() if not v]
    print("ALL HELD" if not bad else
          f"NOT ALL HELD: {[k.split()[0] for k in bad]}\n"
          "-> apply the withdrawal condition in prereg/MASKWIDE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
