"""Real hypergraph-structure statistics and single-fit runtimes on the primary PLCO analysis sample.

Replaces two unsourced items found by the 2026-09-03 audit: figures/structure.pdf (a synthetic power law drawn
in make_figures.py) and the hypergraph-structure paragraph of the results (median supports, starved-pattern
shares, ancestor coverage) whose numbers had no committed source; and the runtime table, whose timings had none.

For each cohort (baseline feature set, the run_h1_h4 stratified 40,000 subsample, seed 0), on the FULL sample
(not a fold): realised patterns and supports (hgmiss.patterns), immediate ancestors among patterns with support
>= 30, and the share of records whose pattern has support < 30 / has at least one ancestor. Writes
  results/structure_stats.csv     one row per cohort
  results/structure_support.csv   one row per (cohort, rank): support sorted descending, for the figure
  results/runtime_single_fit.csv  wall-clock seconds of ONE fit + predict per method on ONE 80/20 split
"""
import pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.model_selection import train_test_split
from hgmiss.data.plco import COHORTS, load_cohort
from hgmiss.patterns import extract_patterns, supports_for, immediate_ancestors
from run_h1_h4 import _subsample, FULL_MAX_N, _median_support_kappa, ROOT as PLCO_ROOT
MIN_SUPPORT = 30

def structure(cohort, X, y):
    mask = ~np.isnan(X); realised = extract_patterns(mask); pats = [e for e in realised if e]
    sup = supports_for(pats, mask); fitted = [e for e in pats if sup[e] >= MIN_SUPPORT]
    anc = immediate_ancestors(fitted)
    n = len(X); own = np.array([realised[e] for e in pats]); s = np.array([sup[e] for e in pats])
    starved = s < MIN_SUPPORT
    # a record's own pattern e: does it have at least one fitted pattern strictly inside it (an ancestor)?
    fitted_set = set(fitted)
    has_anc = {e: (e in fitted_set and len(anc.get(e, [])) > 0) or (e not in fitted_set and any(f < e for f in fitted)) for e in pats}
    rec_with_anc = sum(realised[e] for e in pats if has_anc[e])
    root = max(s)
    return dict(cohort=cohort, n=n, d=X.shape[1], n_patterns=len(pats), n_fitted=len(fitted),
                median_support=float(np.median(s)), root_support=int(root), root_share=float(root / n),
                starved_patterns_share=float(starved.mean()), starved_records_share=float(own[starved].sum() / n),
                records_with_ancestor_share=float(rec_with_anc / n),
                exact_match_share=float(sum(realised[e] for e in fitted) / n)), sorted(s, reverse=True)

def runtimes(cohort, X, y):
    from hgmiss.baselines.pattern import pattern_submodels
    from hgmiss.estimator import HypergraphShrinkage
    from sklearn.impute import SimpleImputer; from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    tr, te = train_test_split(np.arange(len(y)), test_size=0.2, stratify=y, random_state=0); Xtr, ytr, Xte = X[tr], y[tr], X[te]
    def t(fn):
        t0 = time.perf_counter(); fn(); return time.perf_counter() - t0
    imp = SimpleImputer(strategy="mean", keep_empty_features=True)
    out = {"mean_impute": t(lambda: LogisticRegression(max_iter=2000).fit(imp.fit_transform(Xtr), ytr).predict_proba(imp.transform(Xte))),
           "mean_indicator": t(lambda: LogisticRegression(max_iter=2000).fit(np.hstack([imp.fit_transform(Xtr), np.isnan(Xtr)]), ytr).predict_proba(np.hstack([imp.transform(Xte), np.isnan(Xte)]))),
           "histgb_native": t(lambda: HistGradientBoostingClassifier(random_state=0).fit(Xtr, ytr).predict_proba(Xte)),
           "pattern_submodels": t(lambda: pattern_submodels(Xtr, ytr, Xte))}
    e0 = HypergraphShrinkage(kappa=1.0).fit(Xtr, ytr); k = _median_support_kappa([])({e: e0.supports_[e] for e in e0.patterns_})
    out["ours"] = t(lambda: HypergraphShrinkage(kappa=k).fit(Xtr, ytr).predict_proba(Xte))
    return [dict(cohort=cohort, method=m, seconds=v, n_train=len(tr)) for m, v in out.items()]

def main():
    stats, ranks, rt = [], [], []
    for cohort in COHORTS:
        c = load_cohort(cohort, PLCO_ROOT, feature_set="baseline"); X, y = _subsample(c, seed=0, max_n=FULL_MAX_N)
        st, s = structure(cohort, X, y); stats.append(st); ranks += [dict(cohort=cohort, rank=i + 1, support=v) for i, v in enumerate(s)]
        print(f"  {cohort}: " + " ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in st.items() if k != "cohort"), flush=True)
        rt += runtimes(cohort, X, y); print(f"  {cohort} runtimes: " + " ".join(f"{r['method']} {r['seconds']:.1f}s" for r in rt if r['cohort'] == cohort), flush=True)
        pd.DataFrame(stats).to_csv(ROOT / "results/structure_stats.csv", index=False)
        pd.DataFrame(ranks).to_csv(ROOT / "results/structure_support.csv", index=False)
        pd.DataFrame(rt).to_csv(ROOT / "results/runtime_single_fit.csv", index=False)

if __name__ == "__main__":
    main()
