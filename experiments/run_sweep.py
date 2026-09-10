"""Run the pre-registered comparison (prereg/SWEEP.md) on every built sweep dataset, flagged or not:
holdout half, 100,000-record subsample, 2 seeds x 5 folds, all arms (run_candidate.py). Sequential; skips datasets
whose results file already has 10 real cells."""
import pathlib, subprocess, sys
import pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent; CACHE = pathlib.Path.home() / ".cache/phd-matrices"
for npz in sorted(p.stem for p in CACHE.glob("sweep_*.npz")):
    out = ROOT / "results/cand" / f"{npz}.csv"
    if out.exists():
        d = pd.read_csv(out)
        if len(d[(d.permuted == 0) & (d.arm == "ours")]) >= 10: print(f"  {npz}: done, skipping", flush=True); continue
    print(f"== {npz}", flush=True)
    subprocess.run([sys.executable, str(HERE / "run_candidate.py"), "--npz", npz, "--seeds", "2", "--folds", "5", "--max-n", "100000"], check=False)
