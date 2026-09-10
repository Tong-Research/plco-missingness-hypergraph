"""Real datasets under the final protocol, plus candidate pre-merge diagnostics.

Two things are produced for every dataset, so that one can be regressed on the other:

1. THE OUTCOME. The proposed method against a *tuned* pooled indicator model, with
   kappa selected by nested inner CV under the conservative rule -- the identical
   harness used for the synthetic factorial (``run_synthetic_suite.one_fold``).
   Earlier real-data numbers in this project were measured against untuned
   baselines and are not comparable with each other; this recomputes all of them
   on the same footing.

2. THE DIAGNOSTICS. Quantities computable *before* fitting the method, which are
   candidates for predicting whether it will help:

   - ``iota``    AUROC(mask -> y) - 0.5, mask informativeness. Included because it
                 is the obvious candidate and because the synthetic study says it
                 should NOT work: a pooled indicator model already absorbs a shift
                 in the base rate.
   - ``cov30``   fraction of records in a pattern of support >= 30, i.e. the
                 fraction for which a local model can be fitted at all. The
                 synthetic study makes this a necessary condition.
   - ``het``     support-weighted divergence between each pattern's local
                 coefficients and the pooled coefficients on the variables they
                 share. This is the quantity the synthetic study identifies as the
                 driver.
   - ``het_excess`` the same statistic minus its value on mask-permuted data.
                 Coefficient divergence is inflated by estimation noise in small
                 patterns, and permuting the mask rows preserves the pattern sizes
                 and the feature distribution while destroying any real
                 pattern-specific structure, so the difference isolates the part of
                 the divergence that is not noise.

Usage: run_real_suite.py [--plco] [--out results/real_suite.csv]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_synthetic_suite import evaluate  # noqa: E402
from synthgen import dataset_stats  # noqa: E402

warnings.simplefilter("ignore")
SENTINELS = {"?", "none", "unknown/invalid", "null", "unknown", "nan", "na"}
MIN_SUPPORT = 15


# --------------------------------------------------------------- data loading
def _from_openml(name=None, data_id=None, drop=(), cap=20000):
    from sklearn.datasets import fetch_openml
    d = fetch_openml(name=name, data_id=data_id, as_frame=True)
    df = d.frame.copy()
    y_raw = df.pop(d.target.name)
    for c in drop:
        df.drop(columns=[c], errors="ignore", inplace=True)
    top = y_raw.astype(str).value_counts().index[0]
    y = (y_raw.astype(str) != top).astype(int).to_numpy()
    cols = []
    for c in df.columns:
        s = df[c]
        if s.dtype.kind in "biufc":
            cols.append(pd.to_numeric(s, errors="coerce").rename(c))
        else:
            ss = s.astype(str).str.strip()
            isna = ss.str.lower().isin(SENTINELS) | s.isna()
            codes = ss.astype("category").cat.codes.astype(float)
            codes[isna.to_numpy()] = np.nan
            cols.append(pd.Series(codes, index=s.index, name=c))
    X = pd.concat(cols, axis=1).to_numpy(float)
    if len(y) > cap:
        keep, _ = train_test_split(np.arange(len(y)), train_size=cap, stratify=y,
                                   random_state=0)
        X, y = X[keep], y[keep]
    return X, y


def _heart_4site():
    """UCI heart disease: four hospitals, each measuring a different subset."""
    import io
    import urllib.request
    cols = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
            "exang", "oldpeak", "slope", "ca", "thal", "num"]
    base = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/"
    frames = []
    for site in ["cleveland", "hungarian", "switzerland", "va"]:
        raw = urllib.request.urlopen(base + f"processed.{site}.data", timeout=30).read().decode()
        frames.append(pd.read_csv(io.StringIO(raw), header=None, names=cols, na_values="?"))
    d = pd.concat(frames, ignore_index=True)
    d.loc[d["chol"] == 0, "chol"] = np.nan          # documented sentinel
    y = (d["num"] > 0).astype(int).to_numpy()
    X = d[cols[:-1]].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    return X, y


def _plco(cohort, cap=20000):
    from hgmiss.data.plco import load_cohort
    from pathlib import Path
    c = load_cohort(cohort, Path(os.environ["PLCO_ROOT"]), feature_set="baseline")
    X, y = c.X, c.y
    if len(y) > cap:
        keep, _ = train_test_split(np.arange(len(y)), train_size=cap, stratify=y,
                                   random_state=0)
        X, y = X[keep], y[keep]
    return X, y


DATASETS = [
    ("heart-4site", _heart_4site),
    ("colic", lambda: _from_openml(name="colic")),
    ("hepatitis", lambda: _from_openml(name="hepatitis")),
    ("primary-tumor", lambda: _from_openml(name="primary-tumor")),
    ("vote", lambda: _from_openml(name="vote")),
    ("cylinder-bands", lambda: _from_openml(name="cylinder-bands")),
    ("eucalyptus", lambda: _from_openml(name="eucalyptus")),
    ("hypothyroid", lambda: _from_openml(name="hypothyroid")),
    ("sick", lambda: _from_openml(name="sick")),
    ("support2", lambda: _from_openml(name="support2")),
    ("Diabetes130US", lambda: _from_openml(data_id=43874,
                                           drop=("readmitted", "readmit_binary"))),
]
def _mimic4(max_n=40_000, seed=0):
    """MIMIC-IV first-ICU-stay matrix (experiments/mimic4_sites.py; 42 first-24h labs, in-hospital
    mortality), the committed replication target for the companion article's MIMIC-IV test, whose
    original extract (28 labs, prevalence 2.7%) was never versioned. Subsampled to the same n."""
    import os
    z = np.load(os.environ.get("MIMIC_NPZ", os.path.expanduser("~/.cache/phd-matrices/mimic4_sites.npz")),
                allow_pickle=True)
    X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
    if max_n and len(X) > max_n:
        idx = np.random.default_rng(seed).choice(len(X), max_n, replace=False); X, y = X[idx], y[idx]
    return X, y


EXTRA_SETS = [("mimic4", _mimic4)]   # opt-in via --only; never part of the eleven-dataset table
PLCO_SETS = [(f"plco-{c}", (lambda c=c: _plco(c))) for c in
             ["colorectal", "lung", "ovarian", "prostate"]]


# ---------------------------------------------------------------- diagnostics
def _pattern_rows(X, min_support=MIN_SUPPORT):
    keys = [tuple(np.flatnonzero(~np.isnan(r)).tolist()) for r in X]
    idx = {}
    for i, k in enumerate(keys):
        idx.setdefault(k, []).append(i)
    return {k: np.asarray(v) for k, v in idx.items()
            if len(v) >= min_support and len(k) > 0}


def _het_statistic(X, y, min_support=MIN_SUPPORT, max_patterns=40):
    """Support-weighted divergence of per-pattern slopes from the pooled slopes."""
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(X)
    Xi = imp.transform(X)
    sc = StandardScaler().fit(Xi)
    Z = sc.transform(Xi)
    if len(np.unique(y)) < 2:
        return 0.0
    pooled = LogisticRegression(max_iter=2000).fit(Z, y).coef_.ravel()
    groups = _pattern_rows(X, min_support)
    if not groups:
        return 0.0
    items = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:max_patterns]
    num = den = 0.0
    for cols, rows in items:
        yy = y[rows]
        if len(np.unique(yy)) < 2:
            continue
        cols = list(cols)
        local = LogisticRegression(max_iter=2000).fit(Z[np.ix_(rows, cols)], yy).coef_.ravel()
        ref = pooled[cols]
        scale = np.linalg.norm(ref) + 1e-9
        num += len(rows) * float(np.linalg.norm(local - ref) / scale)
        den += len(rows)
    return num / den if den else 0.0


def diagnostics(X, y, seed=0):
    rng = np.random.default_rng(seed)
    st = dataset_stats(X, y)
    # iota: can the mask alone predict the outcome?
    M = (~np.isnan(X)).astype(float)
    try:
        tr, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y,
                                  random_state=0)
        lm = LogisticRegression(max_iter=1000).fit(M[tr], y[tr])
        iota = roc_auc_score(y[te], lm.predict_proba(M[te])[:, 1]) - 0.5
    except Exception:
        iota = float("nan")
    het = _het_statistic(X, y)
    # null: permute mask rows -> same pattern sizes, no real structure
    Xh = X.copy()
    col_mean = np.nanmean(X, axis=0)
    col_mean = np.where(np.isfinite(col_mean), col_mean, 0.0)
    nan_idx = np.where(np.isnan(Xh))
    Xh[nan_idx] = np.take(col_mean, nan_idx[1])
    perm = rng.permutation(len(X))
    Xp = Xh.copy()
    Xp[~(~np.isnan(X))[perm]] = np.nan
    het_null = _het_statistic(Xp, y)
    return dict(iota=iota, cov30=st["cov30"], eff_pat=st["eff_pat"],
                n_pat=st["n_pat"], miss=st["miss"], prev=st["prev"],
                het=het, het_null=het_null, het_excess=het - het_null)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plco", action="store_true", help="include the four PLCO cohorts")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="results/real_suite.csv")
    ap.add_argument("--only", default="", help="comma-separated dataset names (DATASETS, PLCO or EXTRA_SETS)")
    a = ap.parse_args()
    sets = DATASETS + (PLCO_SETS if a.plco else []) + EXTRA_SETS
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        sets = [s for s in sets if s[0] in want]
        assert sets, f"--only matched nothing; known: {[s[0] for s in DATASETS + PLCO_SETS + EXTRA_SETS]}"
    rows = []
    for name, load in sets:
        try:
            X, y = load()
            if np.isnan(X).mean() < 0.01:
                print(f"{name:16s} SKIP (no missingness)", flush=True)
                continue
            t = time.time()
            dg = diagnostics(X, y)
            df = evaluate(X, y, list(range(a.seeds)), MIN_SUPPORT, "1se")
            d_ = (df["safe_adaptive"] - df["tuned_indicator"]).to_numpy()
            p = stats.wilcoxon(d_).pvalue if not np.allclose(d_, 0) else 1.0
            rec = dict(dataset=name, n=len(y), d=X.shape[1], **dg,
                       tuned_indicator=df["tuned_indicator"].mean(),
                       tuned_impute=df["tuned_impute"].mean(),
                       safe_adaptive=df["safe_adaptive"].mean(),
                       safe_oracle=df["safe_oracle"].mean(),
                       delta=d_.mean(), p=p, wins=int((d_ > 0).sum()), n_folds=len(d_))
            rows.append(rec)
            verdict = "WIN " if (p < 0.05 and d_.mean() > 0) else \
                      ("LOSS" if (p < 0.05 and d_.mean() < 0) else "tie ")
            print(f"{name:16s} n={len(y):6d} het={dg['het']:.3f} "
                  f"exc={dg['het_excess']:+.3f} c30={dg['cov30']:.2f} "
                  f"iota={dg['iota']:+.3f} | delta={d_.mean():+.4f} p={p:.1e} "
                  f"{verdict} [{time.time()-t:.0f}s]", flush=True)
        except Exception as e:
            print(f"{name:16s} ERROR {type(e).__name__}: {str(e)[:60]}", flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.to_csv(a.out, index=False)
    print(f"\nwrote {a.out} ({len(out)} datasets)")
    if len(out) >= 4:
        print("\nCorrelation of each diagnostic with the observed delta:")
        for c in ["het", "het_excess", "cov30", "iota", "eff_pat", "miss", "n"]:
            v = out[c].to_numpy(float)
            ok = np.isfinite(v)
            if ok.sum() >= 4:
                r = stats.spearmanr(v[ok], out["delta"].to_numpy()[ok])
                print(f"  {c:12s} spearman rho={r.statistic:+.3f} p={r.pvalue:.3f}")


if __name__ == "__main__":
    main()
