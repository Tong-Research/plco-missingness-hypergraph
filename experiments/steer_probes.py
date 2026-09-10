"""Steering probes (2026-09-04, prereg/STEER.md): four development-half experiments that ask where the hypergraph could
matter OTHER than pooled accuracy against a tree. All on DEV halves (hash split), one seed, 3 folds, capped rows; each
writes results/steer/<probe>_<dataset>.csv. Nothing here touches a holdout half.
  smalln   AUPRC of indicator LR / CV hierarchy / native tree as the training set shrinks (n = 500 ... 20000)
  worstpat per-pattern log-loss and AUPRC of the same three arms: worst and median over test patterns with >= 50 rows
  drift    detection delay of a schema drift (a well-observed variable stops being recorded) by a lattice statistic
           (share of records with no fitted training pattern) vs a prediction-shift statistic on the tree
  abstain  selective prediction: retain the 50/70/90 % of records ranked by tree confidence vs by lattice support
  blend    tree + hierarchy combinations: 50/50 average, inner-CV weight, tree stacked on the hierarchy's OOF prediction,
           and the hierarchy fitted on [X, tree OOF logit] (a nonlinear feature under the shrinkage rule)
  robust   extra missingness injected at test time (10 / 30 % of observed values dropped): which arm degrades least
  transfer leave-one-site-out on MIMIC-IV sites (mimic4 only): degradation of each arm under site shift"""
import argparse, csv, pathlib, sys, time, warnings, numpy as np
warnings.simplefilter("ignore"); HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
from run_candidate import tuned, family_cv
from screen_candidates import dev_mask
from mimic_split import dev_mask as mimic_dev
C = pathlib.Path.home() / ".cache/phd-matrices"; CAP = 40_000

def load(name, cap, seed=0):
    if name == "mimic4":
        z = np.load(C / "mimic4_sites.npz", allow_pickle=True); X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); m = mimic_dev(len(X))
    else:
        z = np.load(C / f"{name}.npz", allow_pickle=True); X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int); m = dev_mask(name, len(X))
    X, y = X[m], y[m]
    if len(X) > cap: idx = np.random.default_rng(seed).choice(len(X), cap, replace=False); X, y = X[idx], y[idx]
    return X[:, ~np.isnan(X).all(0)], y

def tree(Xtr, ytr, Xte):
    kc = np.flatnonzero(np.array([len(np.unique(Xtr[~np.isnan(Xtr[:, j]), j])) >= 2 for j in range(Xtr.shape[1])]))
    return HistGradientBoostingClassifier(random_state=0, early_stopping=False).fit(Xtr[:, kc], ytr).predict_proba(Xte[:, kc])[:, 1]

def arms(Xtr, ytr, Xte):
    out = {"mean_indicator": tuned(Xtr, ytr, Xte, "mean_indicator"), "histgb_native": tree(Xtr, ytr, Xte)}
    out["family_cv"], _ = family_cv(Xtr, ytr, Xte); return out

def pat_keys(M): return [r.tobytes() for r in M]

def write(out, rows):
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)", flush=True)

def smalln(name, out):
    X, y = load(name, CAP); rows = []; t0 = time.time()
    tr_all, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y, random_state=0)
    for n in [500, 1000, 2000, 5000, 20000]:
        if n > len(tr_all): continue
        for rep in range(3):
            tr = np.random.default_rng(100 * rep + n).choice(tr_all, n, replace=False)
            if len(np.unique(y[tr])) < 2 or y[tr].sum() < 10: continue
            keep = ~np.isnan(X[tr]).all(0); P = arms(X[tr][:, keep], y[tr], X[te][:, keep])
            for arm, p in P.items(): rows.append(dict(dataset=name, n=n, rep=rep, arm=arm, auprc=average_precision_score(y[te], p), n_test=len(te)))
            print(f"  n={n} rep={rep} " + " ".join(f"{a}={average_precision_score(y[te], p):.4f}" for a, p in P.items()) + f" [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def worstpat(name, out):
    X, y = load(name, CAP); rows = []; t0 = time.time()
    for fold, (tr, te) in enumerate(StratifiedKFold(3, shuffle=True, random_state=0).split(X, y)):
        keep = ~np.isnan(X[tr]).all(0); P = arms(X[tr][:, keep], y[tr], X[te][:, keep]); keys = pat_keys(~np.isnan(X[te][:, keep])); groups = {}
        for i, k in enumerate(keys): groups.setdefault(k, []).append(i)
        big = {k: np.array(v) for k, v in groups.items() if len(v) >= 50 and len(np.unique(y[te][v])) == 2}
        trkeys = {}; 
        for k in pat_keys(~np.isnan(X[tr][:, keep])): trkeys[k] = trkeys.get(k, 0) + 1
        for arm, p in P.items():
            p = np.clip(p, 1e-6, 1 - 1e-6); ll = np.array([log_loss(y[te][v], p[v], labels=[0, 1]) for v in big.values()]); au = np.array([average_precision_score(y[te][v], p[v]) for v in big.values()])
            sup = np.array([trkeys.get(k, 0) for k in big]); small = sup < 300
            rows.append(dict(dataset=name, fold=fold, arm=arm, n_patterns=len(big), worst_logloss=ll.max(), median_logloss=np.median(ll), worst_auprc=au.min(), median_auprc=np.median(au),
                             small_mean_logloss=(ll[small].mean() if small.any() else np.nan), small_mean_auprc=(au[small].mean() if small.any() else np.nan), n_small=int(small.sum()), pooled_auprc=average_precision_score(y[te], p)))
        print(f"  fold {fold}: patterns {len(big)} | " + " | ".join(f"{r['arm']}: worst ll {r['worst_logloss']:.3f} med ll {r['median_logloss']:.3f} worst au {r['worst_auprc']:.3f}" for r in rows[-3:]) + f" [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def drift(name, out):
    from hgmiss.estimator import HypergraphShrinkage
    X, y = load(name, CAP); rows = []; t0 = time.time(); rng = np.random.default_rng(0)
    tr, te = train_test_split(np.arange(len(y)), test_size=0.4, stratify=y, random_state=0); keep = ~np.isnan(X[tr]).all(0); Xtr, Xte = X[tr][:, keep], X[te][:, keep]
    obs = (~np.isnan(Xtr)).mean(0); cands = np.argsort(-obs)[:4]   # four most-observed variables
    kc = np.flatnonzero(np.array([len(np.unique(Xtr[~np.isnan(Xtr[:, j]), j])) >= 2 for j in range(Xtr.shape[1])]))
    model = HistGradientBoostingClassifier(random_state=0, early_stopping=False).fit(Xtr[:, kc], y[tr])
    fitted = {k for k, n in __import__("collections").Counter(pat_keys(~np.isnan(Xtr))).items() if n >= 30}
    W = 500; order = rng.permutation(len(te)); nwin = len(order) // W; half = nwin // 2
    for v in cands:
        for stat in ["lattice_unfitted", "pred_mean_shift", "pred_ks"]:
            vals = []; base = None
            for w in range(nwin):
                idx = order[w * W:(w + 1) * W]; Xw = Xte[idx].copy()
                if w >= half: Xw[:, v] = np.nan          # drift: variable v stops being recorded
                if stat == "lattice_unfitted": s = np.mean([k not in fitted for k in pat_keys(~np.isnan(Xw))])
                else:
                    p = model.predict_proba(Xw[:, kc])[:, 1]
                    if stat == "pred_mean_shift": s = p.mean()
                    else:
                        if base is None: base = p
                        from scipy.stats import ks_2samp; s = ks_2samp(base, p).statistic
                vals.append(s)
            vals = np.array(vals); pre = vals[:half]; mu, sd = pre.mean(), pre.std() + 1e-9; z = (vals[half:] - mu) / sd
            hit = np.flatnonzero(np.abs(z) > 3); delay = int(hit[0]) if len(hit) else -1
            rows.append(dict(dataset=name, variable=int(v), obs_frac=float(obs[v]), stat=stat, windows=nwin, window_size=W, pre_mean=mu, pre_sd=sd, post_first=vals[half], delay_windows=delay, max_abs_z=float(np.abs(z).max())))
            print(f"  var {v} (obs {obs[v]:.2f}) {stat:17s} delay {delay:3d} windows, max|z| {np.abs(z).max():.1f} [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def abstain(name, out):
    X, y = load(name, CAP); rows = []; t0 = time.time()
    for fold, (tr, te) in enumerate(StratifiedKFold(3, shuffle=True, random_state=0).split(X, y)):
        keep = ~np.isnan(X[tr]).all(0); Xtr, Xte = X[tr][:, keep], X[te][:, keep]; p = tree(Xtr, y[tr], Xte)
        trc = {}; 
        for k in pat_keys(~np.isnan(Xtr)): trc[k] = trc.get(k, 0) + 1
        sup = np.array([trc.get(k, 0) for k in pat_keys(~np.isnan(Xte))]); depth = (~np.isnan(Xte)).sum(1)
        scores = {"tree_confidence": np.abs(p - 0.5), "lattice_support": sup + 1e-3 * np.random.default_rng(fold).random(len(sup)), "pattern_depth": depth + 1e-3 * np.random.default_rng(fold).random(len(sup)), "random": np.random.default_rng(fold).random(len(sup))}
        for cov in [0.5, 0.7, 0.9]:
            for rule, s in scores.items():
                keepn = int(cov * len(te)); idx = np.argsort(-s)[:keepn]
                if len(np.unique(y[te][idx])) < 2: continue
                rows.append(dict(dataset=name, fold=fold, coverage=cov, rule=rule, auprc=average_precision_score(y[te][idx], p[idx]), auroc=roc_auc_score(y[te][idx], p[idx]), logloss=log_loss(y[te][idx], np.clip(p[idx], 1e-6, 1 - 1e-6), labels=[0, 1]), prevalence=y[te][idx].mean(), full_auroc=roc_auc_score(y[te], p)))
        print(f"  fold {fold}: " + " | ".join(f"{r['rule']}@{r['coverage']}: {r['auprc']:.3f}" for r in rows[-8:]) + f" [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def _oof(fn, Xtr, ytr, seed=0):
    z = np.empty(len(ytr))
    for t_, v_ in StratifiedKFold(3, shuffle=True, random_state=seed).split(Xtr, ytr): z[v_] = fn(Xtr[t_], ytr[t_], Xtr[v_])
    return z

def blend(name, out):
    from scipy.special import logit as _lg
    X, y = load(name, CAP); rows = []; t0 = time.time()
    for fold, (tr, te) in enumerate(StratifiedKFold(3, shuffle=True, random_state=0).split(X, y)):
        keep = ~np.isnan(X[tr]).all(0); Xtr, Xte, ytr, yte = X[tr][:, keep], X[te][:, keep], y[tr], y[te]
        pt = tree(Xtr, ytr, Xte); ph, _ = family_cv(Xtr, ytr, Xte)
        ot = _oof(tree, Xtr, ytr); oh = _oof(lambda a, b, c: family_cv(a, b, c)[0], Xtr, ytr)
        ws = np.linspace(0, 1, 11); wbest = max(ws, key=lambda w: average_precision_score(ytr, w * ot + (1 - w) * oh))
        zt, zo = _lg(np.clip(pt, 1e-6, 1 - 1e-6)), _lg(np.clip(ot, 1e-6, 1 - 1e-6))
        stack = tree(np.hstack([Xtr, oh[:, None]]), ytr, np.hstack([Xte, ph[:, None]]))                  # tree with the hierarchy's OOF prediction as a column
        hier_on_tree, _ = family_cv(np.hstack([Xtr, zo[:, None]]), ytr, np.hstack([Xte, zt[:, None]]))  # hierarchy with the tree's OOF logit as a column
        P = {"histgb_native": pt, "family_cv": ph, "blend50": 0.5 * pt + 0.5 * ph, "blend_cv": wbest * pt + (1 - wbest) * ph, "stack_tree_on_hier": stack, "hier_on_tree_logit": hier_on_tree}
        for arm, pp in P.items(): rows.append(dict(dataset=name, fold=fold, arm=arm, auprc=average_precision_score(yte, pp), logloss=log_loss(yte, np.clip(pp, 1e-6, 1 - 1e-6), labels=[0, 1]), w_tree=(wbest if arm == "blend_cv" else "")))
        print(f"  fold {fold}: " + " ".join(f"{a}={average_precision_score(yte, pp):.4f}" for a, pp in P.items()) + f" w={wbest:.1f} [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def robust(name, out):
    X, y = load(name, CAP); rows = []; t0 = time.time()
    for fold, (tr, te) in enumerate(StratifiedKFold(3, shuffle=True, random_state=0).split(X, y)):
        keep = ~np.isnan(X[tr]).all(0); Xtr, ytr = X[tr][:, keep], y[tr]
        fits = {"mean_indicator": None, "histgb_native": None, "family_cv": None}
        for frac in [0.0, 0.1, 0.3]:
            Xte = X[te][:, keep].copy(); rng = np.random.default_rng(10 * fold + int(frac * 10))
            if frac > 0:
                obs = np.argwhere(~np.isnan(Xte)); drop = obs[rng.random(len(obs)) < frac]; Xte[drop[:, 0], drop[:, 1]] = np.nan
            P = arms(Xtr, ytr, Xte)
            for arm, pp in P.items(): rows.append(dict(dataset=name, fold=fold, extra_missing=frac, arm=arm, auprc=average_precision_score(y[te], pp), logloss=log_loss(y[te], np.clip(pp, 1e-6, 1 - 1e-6), labels=[0, 1])))
            print(f"  fold {fold} extra {frac}: " + " ".join(f"{a}={average_precision_score(y[te], pp):.4f}" for a, pp in P.items()) + f" [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

def transfer(name, out):
    assert name == "mimic4"
    z = np.load(C / "mimic4_sites.npz", allow_pickle=True); X, y, g = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int), np.asarray(z["g"]).ravel()
    m = mimic_dev(len(X)); X, y, g = X[m], y[m], g[m]; X = X[:, ~np.isnan(X).all(0)]; rows = []; t0 = time.time(); sites = [s for s in np.unique(g) if (g == s).sum() >= 1000]
    for s in sites:
        te, tr = np.flatnonzero(g == s), np.flatnonzero(g != s)
        if len(tr) > CAP: tr = np.random.default_rng(0).choice(tr, CAP, replace=False)
        keep = ~np.isnan(X[tr]).all(0); P = arms(X[tr][:, keep], y[tr], X[te][:, keep])
        # in-site reference: 3-fold CV inside the held-out site
        ins = {a: [] for a in P}
        for t_, v_ in StratifiedKFold(3, shuffle=True, random_state=0).split(X[te], y[te]):
            k2 = ~np.isnan(X[te][t_]).all(0); Q = arms(X[te][t_][:, k2], y[te][t_], X[te][v_][:, k2])
            for a, pp in Q.items(): ins[a].append(average_precision_score(y[te][v_], pp))
        for a, pp in P.items(): rows.append(dict(dataset=name, site=str(s), n_site=len(te), arm=a, auprc_transfer=average_precision_score(y[te], pp), auprc_insite_cv=float(np.mean(ins[a]))))
        print(f"  site {s} (n {len(te)}): " + " ".join(f"{a}: transfer {average_precision_score(y[te], pp):.3f} in-site {np.mean(ins[a]):.3f}" for a, pp in P.items()) + f" [{time.time()-t0:.0f}s]", flush=True)
    write(out, rows)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("probe", choices=["smalln", "worstpat", "drift", "abstain", "blend", "robust", "transfer"]); ap.add_argument("--cap", type=int, default=40_000); ap.add_argument("--dataset", required=True); ap.add_argument("--out", default=None); a = ap.parse_args()
    CAP = a.cap; out = pathlib.Path(a.out) if a.out else ROOT / "results/steer" / f"{a.probe}_{a.dataset}.csv"
    globals()[a.probe](a.dataset, out)
