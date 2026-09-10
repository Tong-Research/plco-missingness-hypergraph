"""Pre-registered comparison on a flagged candidate's HOLDOUT half (prereg/HIGGS.md, prereg/PORTO.md).

    --npz cand_higgs|cand_porto   --seeds 3   --folds 5
Arms: mean_impute (tuned LR), mean_indicator (tuned LR), mask_interaction (tuned LR), histgb_native (defaults),
pattern_submodels, ours (kappa = median support, min_support 30), ours_projected; permuted-mask null for
mean_indicator, mask_interaction and ours (mask rows permuted within the training fold, values mean-filled
first, as in run_real_suite.diagnostics). One row per (arm, permuted, seed, fold) appended per fold to
results/cand/<npz>.csv. Committed before any holdout row exists.
"""
import argparse, os, pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegressionCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from hgmiss.baselines.pattern import pattern_submodels
from hgmiss.estimator import HypergraphShrinkage
from run_h1_h4 import _median_support_kappa
from idea_h_projection import project_unseen
from idea_x_exact import ExactHypergraph
from sklearn.model_selection import StratifiedKFold as _SKF
GRID = [0, 10, 100, 1000, 10_000, 100_000]

def family_cv(Xtr, ytr, Xte):
    """Inner 3-fold CV over fitting rule x kappa; returns prediction and the chosen (rule, kappa)."""
    sc = {}
    for t, v in _SKF(3, shuffle=True, random_state=0).split(Xtr, ytr):
        for k in GRID:
            sc.setdefault(("exact", k), []).append(average_precision_score(ytr[v], ExactHypergraph(kappa=k).fit(Xtr[t], ytr[t]).predict_proba(Xtr[v])))
            sc.setdefault(("support", k), []).append(average_precision_score(ytr[v], HypergraphShrinkage(kappa=float(k)).fit(Xtr[t], ytr[t]).predict_proba(Xtr[v])))
    rule, k = max(sc, key=lambda key: np.mean(sc[key]))
    est = ExactHypergraph(kappa=k) if rule == "exact" else HypergraphShrinkage(kappa=float(k))
    return est.fit(Xtr, ytr).predict_proba(Xte), (rule, k)

def exact_cv(Xtr, ytr, Xte):
    sc = {k: [] for k in GRID}
    for t, v in _SKF(3, shuffle=True, random_state=0).split(Xtr, ytr):
        for k in GRID: sc[k].append(average_precision_score(ytr[v], ExactHypergraph(kappa=k).fit(Xtr[t], ytr[t]).predict_proba(Xtr[v])))
    k = max(GRID, key=lambda kk: np.mean(sc[kk])); return ExactHypergraph(kappa=k).fit(Xtr, ytr).predict_proba(Xte), k
from screen_candidates import dev_mask

def tuned(Xtr, ytr, Xte, kind):
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr); A, B = imp.transform(Xtr), imp.transform(Xte)
    Mtr, Mte = np.isnan(Xtr).astype(float), np.isnan(Xte).astype(float)
    if kind == "mean_indicator": A, B = np.hstack([A, Mtr]), np.hstack([B, Mte])
    if kind == "mask_interaction": A, B = np.hstack([A, Mtr, A * (1 - Mtr)]), np.hstack([B, Mte, B * (1 - Mte)])
    sc = StandardScaler().fit(A)
    return LogisticRegressionCV(Cs=6, cv=3, max_iter=2000, scoring="average_precision").fit(sc.transform(A), ytr).predict_proba(sc.transform(B))[:, 1]

def ours_fit(Xtr, ytr):
    e0 = HypergraphShrinkage(kappa=1.0).fit(Xtr, ytr); k = _median_support_kappa([])({e: e0.supports_[e] for e in e0.patterns_})
    return HypergraphShrinkage(kappa=k).fit(Xtr, ytr), k

def permute_mask(X, rng):
    Xh = X.copy(); mu = np.nanmean(X, axis=0); mu = np.where(np.isfinite(mu), mu, 0.0); idx = np.where(np.isnan(Xh)); Xh[idx] = np.take(mu, idx[1])
    perm = rng.permutation(len(X)); Xp = Xh.copy(); Xp[np.isnan(X)[perm]] = np.nan; return Xp

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--max-n", type=int, default=0); ap.add_argument("--slice", default="holdout", choices=["holdout", "dev-remainder"])
    ap.add_argument("--seed-start", type=int, default=0, help="first seed (jobs split by seed across machines, 2026-09-04)"); ap.add_argument("--out", default=None); ap.add_argument("--resume", action="store_true", help="keep rows already in --out and skip their (seed, fold) cells"); a = ap.parse_args()
    z = np.load(pathlib.Path.home() / ".cache/phd-matrices" / f"{a.npz}.npz", allow_pickle=True)
    X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
    dm = dev_mask(a.npz, len(X))
    if a.slice == "holdout":
        X, y = X[~dm], y[~dm]
    else:   # dev remainder: dev half minus the three fixed subsamples used by the screen, the diagnosis and the kappa path
        di = np.flatnonzero(dm); used = set()
        for seed, size in [(0, 60_000), (0, 120_000), (1, 60_000)]:
            used |= set(di[np.random.default_rng(seed).choice(len(di), min(size, len(di)), replace=False)].tolist())
        keep = np.array([i for i in di if i not in used]); X, y = X[keep], y[keep]
        print(f"  dev-remainder slice: {len(keep):,} of {len(di):,} dev rows untouched", flush=True)
    if a.max_n and len(X) > a.max_n: idx = np.random.default_rng(0).choice(len(X), a.max_n, replace=False); X, y = X[idx], y[idx]
    out = pathlib.Path(a.out) if a.out else ROOT / "results" / "cand" / (f"{a.npz}.csv" if a.slice == "holdout" else f"{a.npz}.devrem.csv"); out.parent.mkdir(parents=True, exist_ok=True); rows = []; t0 = time.time()
    done_cells = set()
    if a.resume and out.exists():
        prev = pd.read_csv(out); cnt = prev.groupby(["seed", "fold"]).size(); full = int(cnt.max()) if len(cnt) else 0
        # "full" means "as many rows as the fullest cell", which can only tell complete from
        # partial when there is something to compare against. With a SINGLE cell on file the
        # max IS that cell's count, so a job killed inside its first cell would mark it done
        # and never redo it -- not hypothetical: SWEEPNULL's eICU p0 and p4 both died in cell 0.
        # One cell is cheap to recompute; ambiguity is not.
        done_cells = ({(int(s), int(f)) for (s, f), n in cnt.items() if n == full}
                      if len(cnt) > 1 else set())   # a cell with fewer rows than the others was cut mid-way: redo it
        rows = prev[[ (int(r.seed), int(r.fold)) in done_cells for r in prev.itertuples()]].to_dict("records"); print(f"  resume: {len(done_cells)} finished cells kept from {out}", flush=True)
    print(f"  {a.npz} HOLDOUT n={len(y):,} prev={y.mean():.4f}", flush=True)
    for seed in range(a.seed_start, a.seed_start + a.seeds):
        for fold, (tr, te) in enumerate(StratifiedKFold(a.folds, shuffle=True, random_state=seed).split(X, y)):
            if (seed, fold) in done_cells: continue
            rng = np.random.default_rng(1000 * seed + fold)
            keepcol = ~np.isnan(X[tr]).all(axis=0)   # a column with no observed value in this training fold carries nothing
            for permuted, Xtr in [(0, X[tr][:, keepcol]), (1, permute_mask(X[tr][:, keepcol], rng))]:
                ytr, Xte, yte = y[tr], X[te][:, keepcol], y[te]
                preds = {}
                for kind in ["mean_impute", "mean_indicator", "mask_interaction"]:
                    if permuted and kind == "mean_impute": continue
                    preds[kind] = tuned(Xtr, ytr, Xte, kind)
                if not permuted:
                    keep = np.array([len(np.unique(Xtr[~np.isnan(Xtr[:, j]), j])) >= 2 for j in range(Xtr.shape[1])])
                    preds["histgb_native"] = HistGradientBoostingClassifier(random_state=0, early_stopping=False).fit(Xtr[:, keep], ytr).predict_proba(Xte[:, keep])[:, 1]
                    preds["pattern_submodels"] = pattern_submodels(Xtr, ytr, Xte)
                est, k = ours_fit(Xtr, ytr); preds["ours"] = est.predict_proba(Xte)
                if not permuted: preds["ours_projected"] = project_unseen(est, Xte, Xtr, ytr, kappa_proj=k).predict_proba(Xte)
                preds["exact_submodels"] = ExactHypergraph(kappa=0).fit(Xtr, ytr).predict_proba(Xte)
                if not permuted: preds["exact_cv"], kx = exact_cv(Xtr, ytr, Xte)
                if not permuted: preds["family_cv"], chosen = family_cv(Xtr, ytr, Xte); print(f"      family_cv chose {chosen}", flush=True)
                if permuted: preds["mean_impute"] = tuned(Xtr, ytr, Xte, "mean_impute")   # same permuted training matrix, for the paired null gain
                for arm, p in preds.items():
                    rows.append(dict(dataset=a.npz, arm=arm, permuted=permuted, seed=seed, fold=fold, auprc=float(average_precision_score(yte, p)), kappa=k, n_test=len(te)))
                # Atomic: to_csv truncates and rewrites the WHOLE accumulated result, so a kill
                # inside that window loses every banked cell, not just this one. These jobs are
                # killed by a wall clock, hundreds of writes in. Write beside it, then rename.
                tmp = out.with_name(out.name + ".tmp"); pd.DataFrame(rows).to_csv(tmp, index=False); os.replace(tmp, out)
            r = {x["arm"]: x["auprc"] for x in rows if x["seed"] == seed and x["fold"] == fold and x["permuted"] == 0}
            print(f"    seed {seed} fold {fold}: " + " ".join(f"{k2[:8]} {v:.4f}" for k2, v in r.items()) + f"  [{time.time()-t0:.0f}s]", flush=True)

if __name__ == "__main__":
    main()
