"""Screen a candidate dataset for the regime the hypergraph estimator targets -- diagnostics ONLY, on the
development half, before any comparison is run (protocol agreed 2026-09-04).

    --npz NAME      ~/.cache/phd-matrices/NAME.npz with X (NaN = missing), y (binary)
Reports on the dev half (hash split, subsampled to --max-n): n, d, prevalence, missing fraction, realised
patterns, support-30 coverage, iota, H, H under the permuted mask, H_exc; and the one cheap comparator
check the screening allows: tuned mean-imputation LR with vs without the indicator on a 70/30 split of the
dev half (AUPRC). Appends one row to results/screen_candidates.csv. Nothing here touches the holdout half.
"""
import argparse, hashlib, pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegressionCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from run_real_suite import diagnostics

def dev_mask(name, n):
    return np.array([int(hashlib.sha1(f"{name}-{i}".encode()).hexdigest(), 16) % 2 == 0 for i in range(n)])

def tuned(Xtr, ytr, Xte, ind):
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr)
    A, B = imp.transform(Xtr), imp.transform(Xte)
    if ind: A = np.hstack([A, np.isnan(Xtr)]); B = np.hstack([B, np.isnan(Xte)])
    sc = StandardScaler().fit(A)
    return LogisticRegressionCV(Cs=6, cv=3, max_iter=1000, scoring="average_precision").fit(sc.transform(A), ytr).predict_proba(sc.transform(B))[:, 1]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--max-n", type=int, default=60_000); a = ap.parse_args()
    z = np.load(pathlib.Path.home() / ".cache/phd-matrices" / f"{a.npz}.npz", allow_pickle=True)
    X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); cols = [str(c) for c in z["cols"]] if "cols" in z else None
    m = dev_mask(a.npz, len(X)); X, y = X[m], y[m]
    if len(X) > a.max_n:
        idx = np.random.default_rng(0).choice(len(X), a.max_n, replace=False); X, y = X[idx], y[idx]
    t0 = time.time(); dg = diagnostics(X, y)
    tr, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y, random_state=0)
    a_imp = average_precision_score(y[te], tuned(X[tr], y[tr], X[te], False)); a_ind = average_precision_score(y[te], tuned(X[tr], y[tr], X[te], True))
    row = dict(dataset=a.npz, n_dev=len(X), d=X.shape[1], **{k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in dg.items()},
               auprc_impute=a_imp, auprc_indicator=a_ind, indicator_gain=a_ind - a_imp, seconds=time.time() - t0)
    out = ROOT / "results/screen_candidates.csv"
    pd.concat([pd.read_csv(out) if out.exists() else pd.DataFrame(), pd.DataFrame([row])], ignore_index=True).to_csv(out, index=False)
    print("  " + " ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))
    flag = (row["het_excess"] >= 0.15) and (row["cov30"] >= 0.9) and (row["iota"] >= 0.05)
    print(f"  FLAG: {'YES -- pre-register a comparison' if flag else 'no'} (rule: H_exc >= 0.15, cov30 >= 0.9, iota >= 0.05)")

if __name__ == "__main__":
    main()
