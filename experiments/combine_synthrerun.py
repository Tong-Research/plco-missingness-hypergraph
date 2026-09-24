"""Build the two synthetic-suite files from the SYNTHRERUN per-mechanism runs (prereg/SYNTHRERUN.md).

results/synthrerun/{1se,argmax}_{MCAR,MAR,MNAR}.csv -> results/synthetic_suite_1se.csv and
results/synthetic_suite.csv, replacing the August files (superseded, not merged). Rows keep the
grid order run_synthetic_suite.py produces, mechanism by mechanism, which is the order
validate_diagnostic.py and make_synth_table.py rely on.

Refuses unless every input has all 36 cells, 25 folds each, and was produced on Linux: the suite
is platform-dependent (Result 232), and a file mixing platforms is the defect this re-run removes.
It also scores R0, that the 1se run reproduces SIMCONTROL's Linux pattern arm exactly.
"""
import glob
import pathlib

import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1] / "results"
MECH = ["MCAR", "MAR", "MNAR"]
OUT = {"1se": "synthetic_suite_1se.csv", "argmax": "synthetic_suite.csv"}


def load(rule):
    parts = []
    for m in MECH:
        f = R / "synthrerun" / f"{rule}_{m}.csv"
        if not f.exists():
            raise SystemExit(f"missing {f.name}: nothing written")
        d = pd.read_csv(f)
        bad = [why for why, ok in [("36 cells", len(d) == 36), ("25 folds", (d.n_folds == 25).all()),
                                   ("one mechanism", (d.mechanism == m).all()),
                                   ("Linux", d.platform.astype(str).str.startswith("Linux").all())] if not ok]
        if bad:
            raise SystemExit(f"{f.name} fails: {', '.join(bad)} (platform {d.platform.unique()}): nothing written")
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def main():
    runs = {rule: load(rule) for rule in OUT}
    sc = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(R / "simcontrol" / "*_pattern.csv")))])
    k = ["mechanism", "het", "info", "concentration", "n"]
    m = runs["1se"].merge(sc, on=k, suffixes=("", "_sc"))
    cols = ["safe_adaptive", "tuned_indicator", "mean_impute", "delta_vs_tuned_ind"]
    same = {c: int((m[c] == m[c + "_sc"]).sum()) for c in cols}
    r0 = len(m) == 108 and all(v == 108 for v in same.values())
    print(f"R0 1se run vs SIMCONTROL Linux pattern arm: {same} of {len(m)} -> {'HELD' if r0 else 'FAILED'}")
    if not r0:
        raise SystemExit("R0 failed: per the prereg nothing is replaced until the difference is explained")
    for rule, d in runs.items():
        d.to_csv(R / OUT[rule], index=False)
        print(f"wrote results/{OUT[rule]} ({len(d)} configurations, platform {d.platform.iloc[0]})")


if __name__ == "__main__":
    main()
