"""Merge per-seed candidate files results/cand/<npz>.s<k>.csv into results/cand/<npz>.csv (2026-09-05). Refuses unless every seed
file holds a full 5-fold set (15 rows x folds), and refuses to shrink an existing merged file. Usage: merge_seed_files.py <npz> <n_seeds>"""
import sys, pathlib, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]; npz, n = sys.argv[1], int(sys.argv[2])
parts = []
for s in range(n):
    f = ROOT / "results/cand" / f"{npz}.s{s}.csv"; d = pd.read_csv(f); cells = d.groupby(["seed", "fold"]).size()
    assert set(d.seed.unique()) == {s}, (f, d.seed.unique()); assert len(cells) == 5 and cells.nunique() == 1, (f, cells.to_dict())
    parts.append(d)
m = pd.concat(parts, ignore_index=True); out = ROOT / "results/cand" / f"{npz}.csv"
if out.exists():
    old = pd.read_csv(out); assert len(m) >= len(old), f"refusing to shrink {out}: {len(old)} -> {len(m)}"; print(f"replacing {out} ({len(old)} rows, {old.groupby(['seed','fold']).ngroups} cells)")
m.to_csv(out, index=False); print(f"wrote {out}: {len(m)} rows, {m.groupby(['seed','fold']).ngroups} cells, arms {sorted(m.arm.unique())}")
