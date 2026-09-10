"""Score the MIMIC-IV pre-registration (prereg/MIMIC.md, approved 2026-09-02 15:46).

Committed BEFORE the run produced a row. Reads results/ideas/M1/mimic4.csv written by
``run_idea.py --idea M1 --cohort mimic4 --max-n 0`` and results/ideas/M1/mimic4.diag.json.
Refuses a missing or short file so a partial run cannot be read as a result. Every test is
paired within (seed, fold): median difference, Wilcoxon, the 0.002 attainable-gain floor, and
the 0.02 cap that prediction 2 carries.

Predictions (numbered as in the prereg):
  P1  regime guard: iota >= 0.18 and H_exc >= 0.15 on the seed-0 training folds
  P2  ours - mean_impute:     median >= 0.002, p < 0.05, AND median < 0.02
  P3  ours - mean_indicator:  median <  0.002 (the honest expectation)
  P4  ours real - ours null (gain over mean_impute, real minus permuted): >= 0.002, p < 0.05
  P5  ours - spsm_global >= 0 and ours - pattern_submodels >= 0 (within family)
  P6  rooted_cv >= mean_impute (median >= -1e-4) and interior kappa in a majority of folds
Withdrawal:
  (a) P1 fails                   (b) ours - mean_impute <= -0.002
  (c) real <= null for ours       (d) any within-family loss (P5 fails) -> bug hunt first
  (e) ours beats mean_indicator by >= 0.002 -> replicate on seeds 10-19 before any prose changes
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
IDEA_DIR = HERE.parent / "results" / "ideas" / "M1"
FLOOR, CAP, PARITY = 0.002, 0.02, 1e-4
ARMS = ["mean_impute", "mean_indicator", "mask_interaction", "histgb_native",
        "pattern_submodels", "spsm_global", "ours", "rooted_cv"]
SEEDS, FOLDS = 10, 5
EXPECTED_ROWS = 2 * SEEDS * FOLDS * len(ARMS)


def paired(piv: pd.DataFrame, a: str, b: str):
    d = (piv[a] - piv[b]).to_numpy()
    d = d[np.isfinite(d)]
    pv = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    return float(np.median(d)), pv, len(d)


def load() -> tuple[pd.DataFrame, dict]:
    parts = sorted(IDEA_DIR.glob("mimic4*.csv"))
    parts = [f for f in parts if ".smoke" not in f.name]
    if not parts:
        raise SystemExit(f"  {IDEA_DIR}/mimic4*.csv MISSING -- refusing to score")
    d = pd.concat([pd.read_csv(f) for f in parts], ignore_index=True)
    d = d.drop_duplicates(subset=["arm", "permuted", "seed", "fold"], keep="last")
    print(f"  read {len(parts)} part file(s)")
    if len(d) < EXPECTED_ROWS:
        raise SystemExit(f"  {len(d)} of {EXPECTED_ROWS} rows -- run incomplete, refusing")
    d["arm"] = d["arm"].str.replace("idea_M1_", "", regex=False)
    missing = set(ARMS) - set(d["arm"])
    if missing:
        raise SystemExit(f"  arms missing from the file: {sorted(missing)} -- refusing")
    g = IDEA_DIR / "mimic4.diag.json"
    diag = json.loads(g.read_text()) if g.exists() else {}
    return d, diag


def main() -> int:
    d, diag = load()
    real = d[d.permuted == 0].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
    null = d[d.permuted == 1].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
    print(f"  MIMIC-IV (M1): {len(d)} rows, {real.shape[0]} real cells, {null.shape[0]} null cells")
    verdicts = {}

    # P1 -- regime guard
    folds = diag.get("train_folds", [])
    if folds:
        iota = float(np.mean([f["iota"] for f in folds]))
        hexc = float(np.mean([f["het_excess"] for f in folds]))
        verdicts["P1"] = (iota >= 0.18) and (hexc >= 0.15)
        print(f"    P1 regime guard   iota {iota:.3f} (>=0.18)  H_exc {hexc:+.3f} (>=0.15)  "
              f"{'HOLDS' if verdicts['P1'] else 'FAILS -> withdrawal (a): stop, report nothing'}")
    else:
        print("    P1 regime guard   diag file missing -- cannot score; treat as NOT HELD")
        verdicts["P1"] = False

    # P2 -- ours vs mean_impute, floor and cap
    m2, p2, n2 = paired(real, "ours", "mean_impute")
    verdicts["P2"] = (m2 >= FLOOR) and (p2 < 0.05) and (m2 < CAP)
    tag = "HOLDS" if verdicts["P2"] else ("FAILS -> withdrawal (b): loses in its own regime"
                                          if m2 <= -FLOOR else "FAILS")
    if m2 >= CAP:
        tag = "EXCEEDS CAP -- a gain this size needs explaining before it is reported"
    print(f"    P2 ours-mean_impute        median {m2:+.6f} p={p2:.3g} n={n2}  {tag}")

    # P3 -- ours vs mean_indicator (honest expectation: below the floor)
    m3, p3, _ = paired(real, "ours", "mean_indicator")
    verdicts["P3"] = m3 < FLOOR
    print(f"    P3 ours-mean_indicator     median {m3:+.6f} p={p3:.3g}  "
          f"{'HOLDS (below floor, as expected)' if verdicts['P3'] else 'FAILS -> condition (e): replicate on seeds 10-19 before any prose changes'}")

    # P4 -- real structure vs its permuted null, as gain over mean_impute in the same cell
    gain_real = real["ours"] - real["mean_impute"]
    gain_null = null["ours"] - null["mean_impute"]
    ex = (gain_real - gain_null).dropna().to_numpy()
    ex_med = float(np.median(ex))
    ex_p = float(stats.wilcoxon(ex).pvalue) if np.any(ex != 0) else 1.0
    verdicts["P4"] = (ex_med >= FLOOR) and (ex_p < 0.05)
    print(f"    P4 real-null (ours gain)   real {gain_real.median():+.6f} null {gain_null.median():+.6f} "
          f"excess {ex_med:+.6f} p={ex_p:.3g}  "
          f"{'HOLDS -- first dataset where real > null' if verdicts['P4'] else 'FAILS -> withdrawal (c): not pattern-structured even here'}")

    # P5 -- within family
    m5a, p5a, _ = paired(real, "ours", "spsm_global")
    m5b, p5b, _ = paired(real, "ours", "pattern_submodels")
    verdicts["P5"] = (m5a >= 0) and (m5b >= 0)
    print(f"    P5 within family           vs spsm {m5a:+.6f} p={p5a:.3g}; vs submodels {m5b:+.6f} p={p5b:.3g}  "
          f"{'HOLDS' if verdicts['P5'] else 'FAILS -> withdrawal (d): bug hunt before reporting anything'}")

    # P6 -- rooted_cv parity and interior kappa
    m6, p6, _ = paired(real, "rooted_cv", "mean_impute")
    kc = d[(d.permuted == 0) & (d.arm == "rooted_cv")]["kappa_chosen"]
    kc = pd.to_numeric(kc, errors="coerce")
    interior = float(np.mean(np.isfinite(kc) & (kc > 0))) if len(kc) else float("nan")
    verdicts["P6"] = (m6 >= -PARITY) and (interior > 0.5)
    print(f"    P6 rooted_cv-mean_impute   median {m6:+.6f} p={p6:.3g}; interior kappa in {interior:.0%} of folds  "
          f"{'HOLDS' if verdicts['P6'] else 'FAILS'}")

    # Every other arm against mean_impute, for the table
    print("    all arms vs mean_impute (paired median, p):")
    for arm in ARMS:
        if arm == "mean_impute":
            continue
        m, p, _ = paired(real, arm, "mean_impute")
        print(f"      {arm:18s} {m:+.6f}  p={p:.3g}")

    held = [k for k, v in verdicts.items() if v]
    failed = [k for k, v in verdicts.items() if not v]
    print(f"\n  held: {held}   failed: {failed}")
    if not verdicts["P1"]:
        print("  OUTCOME: withdrawal (a) -- regime premise fails; report nothing.")
    elif m2 <= -FLOOR:
        print("  OUTCOME: withdrawal (b) -- the method loses in its own regime. Decisive negative.")
    elif verdicts["P2"] and verdicts["P4"] and verdicts["P3"]:
        print("  OUTCOME: beats imputation, not the indicator, beats its null -- the pattern is worth "
              "modelling here and the cheapest way to model it wins.")
    elif verdicts["P2"] and verdicts["P4"] and not verdicts["P3"]:
        print("  OUTCOME: beats the indicator -- condition (e): replicate on seeds 10-19 first.")
    elif verdicts["P2"] and not verdicts["P4"]:
        print("  OUTCOME: gain over imputation but not over the null -- withdrawal (c).")
    else:
        print("  OUTCOME: no gain over imputation -- the negative result is complete across both regimes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
