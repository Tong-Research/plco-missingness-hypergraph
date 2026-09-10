"""Build every dataset of prereg/SWEEP.md mechanically from results/sweep_list.json, then screen it.
Exclusions x2 (< 5 numeric columns with missingness), x3 (download/parse failure), x5 (no default target)
are applied here and written to results/sweep_exclusions.json with the rule that fired."""
import json, pathlib, subprocess, sys, traceback
import numpy as np, pandas as pd
from sklearn.datasets import fetch_openml
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent; CACHE = pathlib.Path.home() / ".cache/phd-matrices"
CAP = 400_000

def build(item):
    d = fetch_openml(data_id=item["did"], as_frame=True, parser="auto", target_column=None)
    ycol = (d.details or {}).get("default_target_attribute")
    if not ycol or "," in ycol or ycol not in d.frame.columns: return None, f"x5 no usable default target ({ycol!r})"
    df = d.frame
    df = df[df[ycol].notna()]   # x7 (amendment 00:36): rows with a missing target are dropped
    yraw = df[ycol]
    if yraw.nunique(dropna=True) == 2:
        vals = sorted(yraw.dropna().unique(), key=str); y = (yraw == vals[-1]).astype(int).to_numpy()
    else:
        ynum = pd.to_numeric(yraw, errors="coerce")
        if ynum.notna().mean() < 0.5: return None, "x5 target not numeric and not binary"
        y = (ynum > ynum.median()).astype(int).to_numpy()
    X = df.drop(columns=[ycol]).apply(pd.to_numeric, errors="coerce")
    X = X.loc[:, X.notna().any()]
    X = X.loc[:, (X.abs().max() <= 1e15)]   # x9 (amendment 01:12): identifier-like columns
    if (X.isna().any()).sum() < 5: return None, f"x2 only {(X.isna().any()).sum()} numeric columns with missingness"
    Xa = np.array(X.to_numpy(float), copy=True); Xa[~np.isfinite(Xa)] = np.nan   # x8 (amendment 00:41)
    if len(Xa) > CAP:
        idx = np.random.default_rng(0).choice(len(Xa), CAP, replace=False); Xa, y = Xa[idx], y[idx]
    if y.mean() in (0.0, 1.0) or min(y.mean(), 1 - y.mean()) * len(y) < 500: return None, "x2 target degenerate (<500 minority rows)"
    return (Xa, y, list(X.columns)), None

def main():
    items = json.load(open(ROOT / "results/sweep_list.json")); excl = {}; built = []
    for it in items:
        name = f"sweep_{it['did']}"; out = CACHE / f"{name}.npz"
        if out.exists(): built.append(name); continue
        res, why = None, None
        for attempt in range(2):
            try: res, why = build(it); break
            except Exception as ex: why = f"x3 {type(ex).__name__}: {str(ex)[:80]}"
        if res is None: excl[it["name"]] = why; print(f"  EXCLUDED {it['name']} ({it['did']}): {why}", flush=True); continue
        X, y, cols = res; np.savez_compressed(out, X=X, y=y, cols=np.array(cols)); built.append(name)
        M = np.isnan(X); print(f"  built {it['name']} -> {name}: n {len(X):,} d {X.shape[1]} prev {y.mean():.3f} missing {M.mean():.1%} patterns {len({r.tobytes() for r in M}):,}", flush=True)
        json.dump(excl, open(ROOT / "results/sweep_exclusions.json", "w"), indent=1)
    json.dump(excl, open(ROOT / "results/sweep_exclusions.json", "w"), indent=1)
    for name in built:
        subprocess.run([sys.executable, str(HERE / "screen_candidates.py"), "--npz", name], check=False)

if __name__ == "__main__":
    main()
