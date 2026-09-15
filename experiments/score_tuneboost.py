"""Score TUNEBOOST against prereg/TUNEBOOST.md (sha256 beb612124491178a).

Written BEFORE any result file existed, so the thresholds cannot be fitted to the numbers. Each
check re-derives its quantity from the CSVs and prints HOLDS / FAILS with the value beside the
registered bar, and the registered withdrawal is printed for every failure so the remedy is not
chosen after the fact.

Comparisons against the main table (proposed method, tuned mean imputation) are NOT paired: this
run is 3 seeds x 5 folds, the main table is 10 x 5 on different partitions. The prereg says so and
no paired test is claimed. The HistGB column comes from Result 171, the same protocol on macOS.
"""
import glob, pathlib, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLCO = ["colorectal", "lung", "ovarian", "prostate"]
FLOOR = 0.002          # the article's attainable-gain floor
ALGOS = ["xgboost", "lightgbm"]


def load_boost():
    fs = sorted(glob.glob(str(ROOT / "results/tune_boost_*.csv")))
    if not fs:
        sys.exit("no results/tune_boost_*.csv yet")
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)


def main() -> int:
    d = load_boost()
    have = sorted(d.cohort.unique())
    main_tbl = pd.read_csv(ROOT / "figures/real_results.csv").set_index("method")
    hist = {}
    for f in sorted(glob.glob(str(ROOT / "results/tune_tree_*.csv"))):
        t = pd.read_csv(f); hist[t.cohort.iloc[0]] = t.auprc_tuned.mean()

    def cell(algo, c):
        return d[(d.algo == algo) & (d.cohort == c)]

    print("=" * 92)
    print("TUNEBOOST — scored against prereg/TUNEBOOST.md (frozen before the run)")
    print("=" * 92)
    print(f"\ncohorts present: {have}\n")
    print(f"{'algo':10s} {'cohort':12s} {'default':>8s} {'tuned':>8s} {'gain(med)':>10s} {'wins':>6s}")
    for algo in ALGOS:
        for c in have:
            s = cell(algo, c)
            if s.empty:
                continue
            g = s.auprc_tuned - s.auprc_default
            print(f"{algo:10s} {c:12s} {s.auprc_default.mean():8.4f} {s.auprc_tuned.mean():8.4f} "
                  f"{g.median():+10.4f} {int((g > 0).sum()):3d}/{len(s):<3d}")

    verdicts = []

    # X1 -- tuning raises both boosters in all 10 cells
    cells = [(a, c) for a in ALGOS for c in have]
    neg = [(a, c, float((cell(a, c).auprc_tuned - cell(a, c).auprc_default).median()))
           for a, c in cells if not cell(a, c).empty
           and (cell(a, c).auprc_tuned - cell(a, c).auprc_default).median() <= 0]
    verdicts.append(("X1", not neg,
                     f"{len(cells) - len(neg)}/{len(cells)} cells with positive paired median gain",
                     "the defaults-understate-a-tree sentence is qualified to name the exception: "
                     + ", ".join(f"{a} on {c} ({g:+.4f})" for a, c, g in neg)))

    # X2 -- XGBoost gains more than LightGBM over the four PLCO cohorts
    gm = {a: pd.Series([float((cell(a, c).auprc_tuned - cell(a, c).auprc_default).median())
                        for c in PLCO if not cell(a, c).empty]).mean() for a in ALGOS}
    verdicts.append(("X2", gm["xgboost"] > gm["lightgbm"],
                     f"mean PLCO gain xgboost {gm['xgboost']:+.4f} vs lightgbm {gm['lightgbm']:+.4f}",
                     "nothing in the article changes; registered so the run can fail at no cost"))

    # X3 -- once tuned the three boosters agree within the floor on >= 3 of 4 PLCO cohorts
    agree = []
    for c in PLCO:
        vals = [cell(a, c).auprc_tuned.mean() for a in ALGOS if not cell(a, c).empty]
        if c in hist:
            vals.append(hist[c])
        if len(vals) == 3:
            agree.append((c, max(vals) - min(vals)))
    n_ok = sum(1 for _, sp in agree if sp <= FLOOR)
    verdicts.append(("X3", len(agree) == 4 and n_ok >= 3,
                     f"{n_ok}/4 cohorts with a three-booster spread <= {FLOOR} "
                     + "; ".join(f"{c} {sp:.4f}" for c, sp in agree),
                     "report the three boosters separately in the main table and state that the "
                     "implementation matters after tuning"))

    # X4 -- both tuned boosters exceed the proposed method on all four PLCO cohorts
    below = []
    for a in ALGOS:
        for c in PLCO:
            if cell(a, c).empty or c not in main_tbl.columns:
                continue
            ours = float(main_tbl.loc["Proposed method", c])
            if cell(a, c).auprc_tuned.mean() <= ours:
                below.append((a, c, cell(a, c).auprc_tuned.mean(), ours))
    verdicts.append(("X4", not below,
                     f"{len(below)} (algo, cohort) cells where the tuned booster does NOT exceed "
                     "the proposed method" + ("".join(f"; {a}/{c} {v:.4f} vs {o:.4f}"
                                                      for a, c, v, o in below)),
                     "state the tuned-tree claim per implementation rather than for 'the tree'"))

    # X5 -- at least one booster beats tuned mean imputation on >= 3 of 4 PLCO cohorts
    beat = 0
    for c in PLCO:
        if c not in main_tbl.columns:
            continue
        imp = float(main_tbl.loc["Mean + logistic", c])
        if any((not cell(a, c).empty) and cell(a, c).auprc_tuned.mean() > imp for a in ALGOS):
            beat += 1
    verdicts.append(("X5", beat >= 3,
                     f"a booster beats tuned mean imputation on {beat}/4 PLCO cohorts",
                     "the practitioner rule is restated: tuning the booster does not reach the "
                     "linear imputation baseline on these cohorts"))

    print("\n" + "-" * 92)
    for k, ok, detail, remedy in verdicts:
        print(f"  {k}  {'HOLDS' if ok else 'FAILS':6s}  {detail}")
        if not ok:
            print(f"       registered withdrawal -> {remedy}")
    n_fail = sum(1 for _, ok, _, _ in verdicts if not ok)
    print("-" * 92)
    print(f"  {len(verdicts) - n_fail} of {len(verdicts)} registered predictions hold")
    if len(have) < 5:
        print(f"  PARTIAL: {len(have)} of 5 datasets present — not the final scoring")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
