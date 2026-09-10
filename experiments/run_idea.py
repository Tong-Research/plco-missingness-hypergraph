"""Run one candidate method under the isolation rules in papers/METHOD-IDEAS.md.

Writes only under results/ideas/<ID>/ (enforced by idea_paths.open_for_write), refuses the
holdout cohorts without --unblind, and produces the permuted-mask null alongside the real arm --
because the bar is the null, not the pooled baseline. A method beating mean imputation by +0.003
whose own null gains +0.004 has found nothing, and the oracle ceiling exists because that is not
hypothetical.

The frozen method's modules are untouched; experiments/frozen_guard.py checks that and should be
run either side of this.
"""
from __future__ import annotations

import argparse
import csv
import os
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from idea_paths import check_cohort, idea_dir, method_name           # noqa: E402
from hgmiss.baselines.simple import mean_impute_lr, mean_indicator_lr  # noqa: E402
from hgmiss.data.plco import load_cohort                              # noqa: E402
from hgmiss.ideas.residual_mask import mean_residual_indicator_lr     # noqa: E402
from hgmiss.ideas.masked_design import masked_lr                    # noqa: E402
from hgmiss.ideas.pattern_blend import group_ids, pattern_blend     # noqa: E402
from hgmiss.ideas.rooted import rooted_cv, rooted_kinf              # noqa: E402
from hgmiss import estimator                                        # noqa: E402
from oracle_ceiling import permute_mask as published_null           # noqa: E402
from run_h1_h4 import _median_support_kappa                         # noqa: E402
from hgmiss.baselines.native import histgb_native                  # noqa: E402
from hgmiss.baselines.pattern import pattern_submodels, spsm_global  # noqa: E402
from hgmiss.baselines.simple import mask_interaction_lr            # noqa: E402
from hgmiss.metrics import evaluate                                   # noqa: E402

_REPO = HERE.parents[2]
ROOT = pathlib.Path(os.environ.get("PLCO_ROOT", _REPO / "datasets" / "plco"))

# Each idea names the arms it needs. The two frozen baselines are included in every run so the
# comparison is within-fold and never against a number copied from another file.
IDEAS = {
    "A4": {
        "mean_impute": mean_impute_lr,
        "mean_indicator": mean_indicator_lr,
        "residual_indicator": mean_residual_indicator_lr,
    },
    # A4b re-runs A4 with the corrected null (Result 141 discarded the first one) and adds the
    # rescaled residual, which the L2-penalty hypothesis predicts will recover what A4 lost.
    # Arms are `masked_design.masked_lr` kinds, not free functions: one design builder, verified
    # against the frozen baselines bit-for-bit, so the arms cannot drift apart.
    # `scaled_residual_indicator` was removed with the kind it named: Result 142 found the
    # rescale is a mathematical no-op because the estimator standardises every column, and
    # retired "residual_scaled" from masked_design.KINDS. This declaration was left behind and
    # nothing noticed until A4b was re-run on a new machine four days later, where it failed
    # identically on both hosts. The validation below now catches that at startup.
    "A4b": {
        "mean_impute": "none",
        "mean_indicator": "raw",
        "residual_indicator": "residual",
    },
    # B7 groups records by missingness pattern and blends each group's own model toward the
    # pooled one, the way Paper C blends a site's model toward the federation's. Arms are
    # handled by `pattern_blend`, not by the kind dispatcher, because they need the group ids
    # and the oracle needs the test labels.
    "B7": {a: a for a in ("pooled", "local", "blend_cv", "blend_oracle")},
    # R1 re-roots the published hierarchy at the imputed model. Plain callables on the function
    # path. `ours_asis` is the frozen estimator at the main table's pre-specified operating
    # point -- kappa = median training-fold support -- so the comparison is against the number
    # the article reports. Its null is the PUBLISHED one from oracle_ceiling.py, not this
    # file's permute_mask, which Result 141 discarded.
    "R1": {
        "mean_impute": mean_impute_lr,
        "ours_asis": estimator.fit_predict(kappa=_median_support_kappa([])),
        "rooted_kinf": rooted_kinf,
        "rooted_cv": rooted_cv,
    },
}
# M1 = prereg/MIMIC.md (approved 2026-09-02 15:46). The seven main-table methods at their
# published operating points -- ours and spsm_global at median training-fold support, built the
# way run_h1_h4.main() builds them -- plus rooted_cv. Cohort "mimic4", --max-n 0 (full cohort).
IDEAS["M1"] = {
    "mean_impute": mean_impute_lr,
    "mean_indicator": mean_indicator_lr,
    "mask_interaction": mask_interaction_lr,
    "histgb_native": histgb_native,
    "pattern_submodels": pattern_submodels,
    "spsm_global": (lambda X_tr, y_tr, X_te, _k=_median_support_kappa([]):
                    spsm_global(X_tr, y_tr, X_te, kappa=_k)),
    "ours": estimator.fit_predict(kappa=_median_support_kappa([])),
    "rooted_cv": rooted_cv,
}
PUBLISHED_NULL_IDEAS = {"R1", "M1"}
COLUMNS = ["idea", "cohort", "arm", "permuted", "seed", "fold", "auprc", "auroc", "n_test",
           "kappa_chosen"]   # R1 only; other ideas leave it empty


def permute_mask(X, rng):
    """Shuffle mask ROWS across records, preserving the pattern set, the supports and the feature
    distribution while destroying the association between pattern and outcome. The same null the
    oracle ceiling uses."""
    X = np.asarray(X, float)
    M = ~np.isnan(X)
    perm = rng.permutation(len(X))
    out = np.where(M[perm], np.nan_to_num(X, nan=0.0), np.nan)
    # keep the observed VALUES where the permuted mask says observed; a cell observed under the
    # permuted mask but missing in the original has no value, so fill from the column mean.
    mu = np.nanmean(X, axis=0)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    need = M[perm] & ~M
    out[need] = np.take(mu, np.where(need)[1])
    out[~M[perm]] = np.nan
    return out


def main() -> int:
    from sklearn.model_selection import StratifiedKFold

    ap = argparse.ArgumentParser()
    ap.add_argument("--idea", required=True, choices=sorted(IDEAS))
    ap.add_argument("--cohort", required=True)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--max-n", type=int, default=40000)
    ap.add_argument("--seed-start", type=int, default=0,
                    help="first seed of this job (M1 runs one seed per job; a full run is 10 jobs x 2 arms)")
    ap.add_argument("--arm", choices=["both", "real", "null"], default="both",
                    help="which arm this job computes; 'both' is the historical single-process run")
    ap.add_argument("--unblind", action="store_true",
                    help="permit a holdout cohort; an idea tuned on the holdout has no holdout")
    a = ap.parse_args()
    check_cohort(a.cohort, a.unblind)

    arms = IDEAS[a.idea]
    # Every declared arm must resolve to something that still exists. A stale name costs a full
    # cohort load and a traceback deep in the fold loop otherwise, and on a fresh machine it
    # looks like a provisioning failure rather than a code one.
    if all(isinstance(v, str) for v in arms.values()) and not a.idea.startswith("B7"):
        from hgmiss.ideas.masked_design import KINDS as _K
        _bad = {k: v for k, v in arms.items() if v not in _K}
        if _bad:
            raise SystemExit(f"  idea {a.idea!r} declares arms whose kinds no longer exist: "
                             f"{_bad}; masked_design.KINDS is {_K}")
    if a.cohort == "mimic4":
        npz = pathlib.Path(os.environ.get(
            "MIMIC_NPZ", pathlib.Path.home() / ".cache" / "phd-matrices" / "mimic4_sites.npz"))
        z = np.load(npz, allow_pickle=True)
        X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
    else:
        c = load_cohort(a.cohort, ROOT, feature_set="baseline")
        X, y = np.asarray(c.X, float), np.asarray(c.y).ravel()
    if a.max_n > 0 and len(X) > a.max_n:
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X), a.max_n, replace=False)
        X, y = X[idx], y[idx]
    print(f"  {a.idea} on {a.cohort}: n={len(X):,} d={X.shape[1]} prev={y.mean():.2%}", flush=True)

    kind_based = (all(isinstance(v, str) for v in arms.values())
                  and not a.idea.startswith("B7"))
    stem = f"{a.cohort}.smoke" if os.environ.get("MIMIC_SMOKE_OUT") else a.cohort
    split = a.arm != "both" or a.seed_start != 0 or a.seeds != 5
    part = f".s{a.seed_start}-{a.seed_start + a.seeds - 1}.{a.arm}" if (a.arm != "both" or a.seed_start) else ""
    out = idea_dir(a.idea) / f"{stem}{part}.csv"
    rows, t0 = [], time.time()
    if a.idea == "M1" and a.seed_start == 0 and a.arm in ("both", "real"):
        # prediction 1's guard: iota and H_exc on the seed-0 TRAINING folds, never on test rows
        from run_real_suite import diagnostics
        import json as _json
        cv0 = StratifiedKFold(n_splits=a.folds, shuffle=True, random_state=0)
        folds = []
        for fold, (tr, _te) in enumerate(cv0.split(X, y)):
            dg = diagnostics(X[tr], y[tr], seed=0)
            folds.append({"fold": fold, **{k: float(v) for k, v in dg.items()}})
        (idea_dir(a.idea) / f"{stem}.diag.json").write_text(_json.dumps(
            {"n": int(len(X)), "d": int(X.shape[1]), "prev": float(y.mean()),
             "train_folds": folds}, indent=1))
        print(f"  seed-0 training-fold diagnostics: iota {np.mean([f['iota'] for f in folds]):.3f} "
              f"H_exc {np.mean([f['het_excess'] for f in folds]):+.3f}", flush=True)
    arms_to_run = {"both": (False, True), "real": (False,), "null": (True,)}[a.arm]
    def _flush():
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerows(rows)
    for permuted in arms_to_run:
        # kind-based ideas permute the mask block inside the design and never touch the values;
        # the older function-based path rebuilds X and is retained only to reproduce Result 141.
        if kind_based or not permuted:
            Xp = X
        elif a.idea in PUBLISHED_NULL_IDEAS:
            Xp = published_null(X, seed=12345)          # oracle_ceiling's null, unchanged
        else:
            Xp = permute_mask(X, np.random.default_rng(12345))
        for seed in range(a.seed_start, a.seed_start + a.seeds):
            cv = StratifiedKFold(n_splits=a.folds, shuffle=True, random_state=seed)
            for fold, (tr, te) in enumerate(cv.split(Xp, y)):
                for label, fn in arms.items():
                    if a.idea.startswith("B7"):
                        # the null regroups records; it never touches values or outcomes
                        g = group_ids(Xp, np.random.default_rng(4321) if permuted else None)
                        p = pattern_blend(Xp[tr], y[tr], Xp[te], arm=fn, g_tr=g[tr],
                                          g_te=g[te], y_te=y[te], seed=seed * 100 + fold)
                    elif kind_based:
                        p = masked_lr(Xp[tr], y[tr], Xp[te], kind=fn,
                                      perm_seed=(9000 + seed * 10 + fold) if permuted else None)
                    else:
                        extra = {}
                        if label == "rooted_cv":
                            p = fn(Xp[tr], y[tr], Xp[te], seed=seed * 100 + fold, record=extra)
                        else:
                            p = fn(Xp[tr], y[tr], Xp[te])
                    m = evaluate(y[te], p)
                    rows.append({"idea": a.idea, "cohort": a.cohort,
                                 "arm": method_name(a.idea, label), "permuted": int(permuted),
                                 "seed": seed, "fold": fold, "auprc": m["auprc"],
                                 "auroc": m["auroc"], "n_test": len(te),
                                 "kappa_chosen": (extra.get("kappa_chosen", "") if "extra" in dir() else "")})
            _flush()   # partial file after every seed; a timeout loses at most one seed
            print(f"    {'permuted' if permuted else 'real    '} seed {seed} done "
                  f"({time.time() - t0:.0f}s)", flush=True)
    _flush()
    print(f"\n  wrote {out} ({len(rows)} rows) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
