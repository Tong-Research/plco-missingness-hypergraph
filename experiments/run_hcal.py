"""HCAL runner (pre-registered in prereg/HCAL.md): pattern-hierarchical Platt calibration wrapped around a fixed native tree.
Arms per cell: tree; tree + global Platt; tree + per-pattern Platt with kappa = 0 (no shrinkage; ablation); tree + hierarchical Platt
with kappa chosen by inner 3-fold CV on log-loss over {10, 100, 1000, 10000}. 3 seeds x 5 stratified folds on ONE slice (dev or holdout),
subsampled to --cap rows with a fixed generator. Per cell and arm: AUPRC, log-loss, Brier, and the same three restricted to test rows
whose training pattern support is below 300 (small patterns). Writes one CSV row per cell x arm."""
import argparse, csv, pathlib, sys, time, warnings, numpy as np
warnings.simplefilter("ignore"); HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "src"))
from scipy.special import logit as _logit, expit
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, log_loss, brier_score_loss
from idea_c_hcal import HierCalibrator, oof_logits, _platt, _guarded_fit_predict
from screen_candidates import dev_mask
from mimic_split import dev_mask as mimic_dev
C = pathlib.Path.home() / ".cache/phd-matrices"; CFG = dict(max_depth=3, learning_rate=0.03, max_iter=500, min_samples_leaf=100); KAPPAS = [10, 100, 1000, 10000]

def load(name, slice_, cap):
    if name == "mimic4":
        z = np.load(C / "mimic4_sites.npz", allow_pickle=True); X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); m = mimic_dev(len(X))
    else:
        z = np.load(C / f"{name}.npz", allow_pickle=True); X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); m = dev_mask(name, len(X))
    if slice_ == "holdout": m = ~m
    X, y = X[m], y[m]
    if len(X) > cap: idx = np.random.default_rng(0).choice(len(X), cap, replace=False); X, y = X[idx], y[idx]
    return X[:, ~np.isnan(X).all(0)], y

def keep(Xtr): return np.flatnonzero(np.array([len(np.unique(Xtr[~np.isnan(Xtr[:, j]), j])) >= 2 for j in range(Xtr.shape[1])]))

def metrics(y, p):
    if len(y) < 2 or y.min() == y.max(): return (np.nan,) * 3
    return average_precision_score(y, p), log_loss(y, p, labels=[0, 1]), brier_score_loss(y, p)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); ap.add_argument("--slice", choices=["dev", "holdout"], required=True)
    ap.add_argument("--cap", type=int, default=60_000); ap.add_argument("--switch", action="store_true", help="add the switch_cv arm (global vs kappa=0 by inner CV)"); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--out", required=True); a = ap.parse_args()
    X, y = load(a.dataset, a.slice, a.cap); t0 = time.time(); rows = []
    print(f"{a.dataset} {a.slice}: {len(y)} rows x {X.shape[1]} cols, prevalence {y.mean():.3f}", flush=True)
    for seed in range(a.seeds):
        for fold, (tr, te) in enumerate(StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y)):
            Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]; kc = keep(Xtr); mk = lambda: HistGradientBoostingClassifier(random_state=0, early_stopping=False, **CFG)
            z_oof = oof_logits(mk, Xtr[:, kc], ytr, seed=seed); z_te = _logit(np.clip(_guarded_fit_predict(mk, Xtr[:, kc], ytr, Xte[:, kc]), 1e-6, 1 - 1e-6))
            Mtr, Mte = ~np.isnan(Xtr), ~np.isnan(Xte)
            trkeys = {}; [trkeys.setdefault(r.tobytes(), 0) for r in Mtr]
            for r in Mtr: trkeys[r.tobytes()] += 1
            small = np.array([trkeys.get(r.tobytes(), 0) < 300 for r in Mte])
            ga, gb = _platt(z_oof, ytr)
            P = {"tree": expit(z_te), "global": expit(ga + gb * z_te), "pattern_k0": HierCalibrator(kappa=0.0).fit(z_oof, ytr, Mtr).transform(z_te, Mte)}
            best, bl = None, np.inf
            for k in KAPPAS:
                ll = [log_loss(ytr[v], HierCalibrator(kappa=k).fit(z_oof[t], ytr[t], Mtr[t]).transform(z_oof[v], Mtr[v]), labels=[0, 1]) for t, v in StratifiedKFold(3, shuffle=True, random_state=1).split(Xtr, ytr)]
                if np.mean(ll) < bl: best, bl = k, float(np.mean(ll))
            P["hier_cv"] = HierCalibrator(kappa=best).fit(z_oof, ytr, Mtr).transform(z_te, Mte)
            if a.switch:   # post-hoc comparator (referee 5, 2026-09-04): choose global vs per-pattern (kappa=0) Platt by the same inner CV
                lg, lk = [], []
                for t_, v_ in StratifiedKFold(3, shuffle=True, random_state=1).split(Xtr, ytr):
                    a_, b_ = _platt(z_oof[t_], ytr[t_]); lg.append(log_loss(ytr[v_], np.clip(expit(a_ + b_ * z_oof[v_]), 1e-6, 1 - 1e-6), labels=[0, 1]))
                    lk.append(log_loss(ytr[v_], HierCalibrator(kappa=0.0).fit(z_oof[t_], ytr[t_], Mtr[t_]).transform(z_oof[v_], Mtr[v_]), labels=[0, 1]))
                sw = "global" if np.mean(lg) <= np.mean(lk) else "k0"; P["switch_cv"] = P["global"] if sw == "global" else P["pattern_k0"]
            for arm, p in P.items():
                au, ll, br = metrics(yte, p); sau, sll, sbr = metrics(yte[small], p[small])
                rows.append(dict(dataset=a.dataset, slice=a.slice, seed=seed, fold=fold, arm=arm, kappa=(best if arm == "hier_cv" else (0 if arm == "pattern_k0" else (sw if arm == "switch_cv" else ""))), n_test=len(yte), n_small=int(small.sum()), auprc=au, logloss=ll, brier=br, small_auprc=sau, small_logloss=sll, small_brier=sbr))
            print(f"  seed {seed} fold {fold}: " + " ".join(f"{k}={average_precision_score(yte, p):.4f}" for k, p in P.items()) + f" kappa={best} [{time.time()-t0:.0f}s]", flush=True)
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
if __name__ == "__main__": main()
