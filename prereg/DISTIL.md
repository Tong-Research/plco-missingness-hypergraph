# DISTIL: distilling a native tree onto the realised pattern poset (pre-registered 2026-09-06 11:20)

Idea 2 of the 2026-09-06 round. The metric is fidelity to the tree, not outcome accuracy, so the tree's lead on the
outcome is not a loss here. The claim under test: a per-pattern linear surrogate, shrunk along the poset, explains a
native tree better than one global linear surrogate with indicators, and shrinkage is what keeps the small patterns usable.

## Design (`experiments/probe_distil.py`)
17 registered datasets, holdout halves capped at 50,000. Two 50/50 stratified splits (seeds 0, 1). Teacher: HistGB
(HCAL config) on the train half; targets are its logits. Surrogates are ridge regressions on standardised mean-filled
values: global (values + indicators, RidgeCV); pattern_k0 (one per realised pattern with support >= 30, own observed
columns, no pull); hier_kappa for kappa in {10, 100, 1000, 10000} (pulled toward the largest-support immediate ancestor,
root toward global; coordinates the ancestor lacks are pulled toward global); hier_cv (kappa by inner 3-fold CV on
train fidelity). Unfitted test patterns use the deepest fitted ancestor, else global. Metrics: fidelity R^2 to the
teacher logit on the test half, and the same restricted to test rows whose pattern has train support < 300; AUPRC of
the surrogate against y is recorded but is not a criterion. Per dataset, the median over the two seeds.

## Predictions
P1. hier_cv R^2 >= global R^2 + 0.02 on >= 9 of 17 datasets.
P2. hier_cv R^2 >= pattern_k0 R^2 - 0.01 on >= 15 of 17 (shrinkage never costs much) AND hier_cv > pattern_k0 + 0.01 on
    >= 5 of 17 (it helps somewhere).
P3. On the small-support rows, hier_cv R^2 >= pattern_k0 R^2 + 0.02 on >= 8 of the datasets that have >= 200 such rows.
P4. Fidelity is not trivially saturated: global R^2 < 0.95 on >= 12 of 17.

## Withdrawal
(a) P1 fails -> per-pattern surrogates add nothing over a global indicator-linear surrogate; the idea is dead.
(b) P2 fails -> shrinkage is unnecessary or harmful for distillation; only the unshrunk per-pattern surrogate could be
    kept, and only if P1 held for pattern_k0 in place of hier_cv.
(c) P3 fails -> the poset buys nothing where it was supposed to (small patterns); any paper is about per-pattern
    surrogates, not about the hierarchy.
(d) P4 fails -> a linear surrogate already explains the tree; nothing to distil. Dropped.

## Disclosure (appended 2026-09-06 11:40)
A smoke test on dugong ran the script on sweep_46654 only (a 4-pattern dataset with no small patterns), to check it runs; its numbers are not used. Predictions were not edited after it.

## Outcome (2026-09-06 12:15; 17/17 datasets on the farm; scorer `experiments/score_probes.py`)

P1 FAILS (hier_cv >= global + 0.02 on 5/17), P2 HOLDS (17/17 and 8/17), P3 HOLDS (8/11), P4 HOLDS (17/17).
Withdrawal (a) fires: per-pattern surrogates, shrunk or not, do not explain the tree better than one global ridge on
values plus indicators. What survives is internal to the poset family: shrinkage never costs more than 0.01, helps by
more than 0.01 on 8 datasets, and on small-support rows beats the unshrunk surrogate by >= 0.02 on 8 of 11. On the two
ICU regime datasets the unshrunk surrogate collapses (R^2 0.04 and 0.32) and shrinkage recovers it (0.36, 0.65) but
never reaches global (0.84, 0.83); sweep_42080 and sweep_42093 are negative for every poset surrogate. Dropped as an
interpretability paper; the shrinkage-rescues-small-patterns fact is already Paper 1's.
Amendment: sweep_42080 and sweep_46725 first crashed with HistGB's window-shape error on near-constant columns; the
guard from run_hcal.keep() was added and both were rerun (12:15). No criterion changed.

Scorer output, verbatim:

```
=== DISTIL (17/17 datasets) ===
P1 hier_cv >= global + 0.02 on 5/17 needs >= 9: FAILS
P2 hier_cv >= k0 - 0.01 on 17/17 (needs >= 15) and > k0 + 0.01 on 8/17 (needs >= 5): HOLDS
P3 small-support rows hier_cv >= k0 + 0.02 on 8/11 eligible needs >= 8: HOLDS
P4 global R2 < 0.95 on 17/17 needs >= 12: HOLDS
                    global  pattern_k0  hier_cv  global_small  pattern_k0_small  hier_cv_small  n_small
dataset                                                                                                
cand_acs_income      0.922       0.891    0.918         0.928             0.861          0.910    11576
cand_airbnb          0.750       0.800    0.800         0.592             0.762          0.764     1367
cand_eicu_regime     0.835       0.037    0.356         0.835             0.036          0.356    23571
cand_higgs           0.596       0.652    0.652           NaN               NaN            NaN        0
cand_mimic4_regime   0.830       0.317    0.647         0.824             0.238          0.616    13712
cand_nhanes          0.851       0.760    0.806         0.895             0.728          0.816     2437
cand_porto           0.574       0.569    0.588         0.641             0.397          0.651     1100
sweep_41275          0.396       0.440    0.440        -2.460             0.368          0.376      115
sweep_42080          0.308      -0.642   -0.031        -4.300          -130.009        -53.689      166
sweep_42093          0.182      -8.370   -0.098         0.037           -21.491         -0.779    10645
sweep_42136          0.771       0.789    0.789         0.721             0.778          0.780      718
sweep_42333          0.920       0.920    0.924         0.885             0.848          0.863     7944
sweep_42737          0.938       0.949    0.956         0.821             0.573          0.788      837
sweep_42739          0.568       0.574    0.604         0.570             0.438          0.590     4616
sweep_46654          0.927       0.926    0.927           NaN               NaN            NaN        0
sweep_46703          0.746       0.748    0.749           NaN               NaN            NaN        0
sweep_46725          0.176       0.290    0.290         0.004             0.193          0.250      116
```
