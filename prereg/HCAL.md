# Pre-registration: pattern-hierarchical calibration around a native missing-value tree (APPROVED)

Status: APPROVED by the user 2026-09-04 21:51 ("Approve, freeze and run"). Drafted 19:20 after the dev-half paired probe (Result 190). No holdout record has been read by the
runner. Approval and a hash in MANIFEST.md freeze it. Runner `experiments/run_hcal.py`, scorer `experiments/score_hcal.py`.

## Claim under test

C1 The published shrinkage rule of the missingness hypergraph, applied to the two Platt parameters (a_e, b_e) of a per-pattern
   recalibration of ANY base model's logits instead of to regression coefficients, gives a model-agnostic wrapper that
   (i) never costs ranking, (ii) lowers log-loss, and (iii) is what makes per-pattern recalibration safe: without shrinkage
   (kappa = 0) the same wrapper damages datasets with many small patterns.
C2 The gain in ranking is small (under 0.01 AUPRC) and is largest where patterns are many; the wrapper is a calibration
   result, not a replacement for the tree.

## Dev evidence (Result 190, dev halves, 15 paired cells each)

road_safety hier +0.0056 AUPRC (p 6e-5), k0 +0.0029; MIMIC hier +0.0003 (p 0.04), k0 -0.0142; Higgs hier +0.0003, k0 +0.0005;
ACS hier +0.0003, k0 -0.0094. Log-loss lower with hier on all four; lower with k0 on two.

## Data and design (holdout halves only)

Seventeen datasets: the ten OpenML sweep sets (sweep_41275, 42080, 42093, 42136, 42333, 42737, 42739, 46654, 46703, 46725),
cand_higgs, cand_porto, cand_acs_income, cand_airbnb, cand_nhanes, cand_mimic4_regime, and MIMIC-IV first stays (mimic4).
eICU regimes are excluded (their holdout is in use by SHOWCASE G2). Holdout half by the registered hash split, subsampled to at
most 60,000 rows with generator seed 0. Base model fixed in advance: HistGradientBoosting, depth 3, rate 0.03, 500 iterations,
min leaf 100, no early stopping, columns with fewer than two observed values dropped per fold. Three seeds x five stratified
folds. Arms: tree; tree + global Platt; tree + per-pattern Platt with kappa = 0 (min support 30; ablation); tree + hierarchical
Platt with kappa chosen by inner 3-fold CV on log-loss over {10, 100, 1000, 10000}. Out-of-fold logits from 3 folds inside the
training fold feed every calibrator. Metrics per cell: AUPRC, log-loss, Brier, and each restricted to test rows whose training
pattern has support below 300. Paired cell-wise differences against the tree; median and Wilcoxon.

## Predictions

P1 Never worse: on every dataset the hierarchical arm's median paired AUPRC difference to the tree is >= -0.002.
P2 Calibration: on at least 12 of 17 datasets the hierarchical arm's log-loss is below the tree's with p < 0.05.
P3 Attribution: on every dataset the hierarchical arm's median log-loss difference is <= the kappa = 0 arm's, and on at least
   three datasets the kappa = 0 arm is worse than the tree in AUPRC by more than 0.005 while the hierarchical arm is not.
P4 Ranking: the hierarchical arm beats the tree in AUPRC with p < 0.05 on at least 6 of 17 datasets, and by more than 0.003
   on road_safety; no dataset beats the tree by more than 0.02 (stated so the result is not later sold as accuracy).
P5 Global Platt changes AUPRC by exactly 0 on every cell (sanity; monotone map).

## Withdrawal

(a) P1 fails on two or more datasets -> the wrapper is not safe; report as a negative and do not recommend it.
(b) P2 fails -> the calibration claim is dropped; the wrapper is reported only as an ablation of the shrinkage rule.
(c) P3 fails (kappa = 0 as good as or better than hierarchical on log-loss on 3+ datasets) -> the hierarchy is not what makes it
    work; the result is ordinary Mondrian recalibration and is prior art (Platt per group); no claim for the hypergraph.
(d) P4 fails -> report calibration only; the abstract's conclusions paragraph is not changed.

## Reporting (Paper 1)

If P1-P3 hold: one paragraph in results ("the shrinkage rule as a calibration wrapper"), one table (17 rows: tree, k0, hier
AUPRC and log-loss deltas, kappa range), one sentence in the abstract's conclusions, one deployment-checklist line. If P4 also
holds, the sentence may say "small ranking gains where patterns are many". Otherwise the paper reports the outcome in one
sentence in the discussion, as with Results 187, 189 and 191.

## Amendment (2026-09-04 22:05, during the run; robustness only)

sweep_42333 crashed on spinner in the inner out-of-fold fit ("window shape cannot be larger than input array shape", the
HistGradientBoosting binning error on a column with almost no observed values in the fit rows). `_guarded_fit_predict` in
`experiments/idea_c_hcal.py` now retries that fit with such columns dropped, only when the error is raised; runs that never
raise it are bit-for-bit unchanged, so the 16 other datasets' outputs stand. Job requeued. No prediction or arm changed.

## Outcome (appended 2026-09-04 22:15; scorer `experiments/score_hcal.py` and `figures/make_hcal_table.py` on `results/hcal/*.csv`, 17 datasets, 15 cells each)

P1 HOLDS: 17/17 median paired AUPRC delta >= -0.002 (worst -0.0002, sweep_46725).
P2 FAILS by one: log-loss below the tree at p < 0.05 on 11/17 (needed 12). Never significantly above it; the misses are datasets
   where the tree is already at AUPRC 0.99-1.00 or the median delta is 0.0000 (public_procurement, la_crimes, NHANES, Porto,
   fps, federal_election, jigsaw_46725). Withdrawal (b) applies: no headline calibration claim.
P3 FAILS on its first clause, HOLDS on its second: hierarchical log-loss <= kappa = 0 on 12/17; the five misses are by 0.0001-0.0003
   on datasets with 5-16 patterns (Higgs, wine-reviews, jigsaw x2, Crime) where the CV picks kappa = 10 and the two arms nearly
   coincide. kappa = 0 is worse than the tree by more than 0.005 AUPRC on four datasets (MIMIC regimes -0.080, MIMIC first stays
   -0.036, ACS -0.019, NHANES -0.018) while the hierarchical arm is within 0.0004 of the tree on all four. Withdrawal (c) applies
   as written: where per-pattern (Mondrian) recalibration is already safe the hierarchy does not improve on it, and the paper
   makes no claim of better calibration than Mondrian. What survives is the second clause, reported as an ablation fact: the
   shrinkage rule is what makes per-pattern recalibration safe when patterns are many.
P4 HOLDS: AUPRC above the tree at p < 0.05 on 7/17; road_safety +0.0081 (> 0.003); maximum +0.0081 (< 0.02). But the kappa = 0 arm
   is +0.0074 on road_safety, so the ranking gain is mostly Mondrian recalibration; the hierarchy adds 0.0007 there.
P5 HOLDS: global Platt changes AUPRC by exactly 0 on every one of the 255 cells.

Reporting decision: P1, P4, P5 hold; P2 and P3(i) fail; (b) and (c) apply. Paper 1 gets one results subsection and the table, worded
as an ablation of the shrinkage rule around a fixed tree: never worse than the tree (17/17), lower log-loss on 11, small ranking
gains on 7 (max +0.008), and the kappa = 0 comparison showing that the rule is the safety device that lets per-pattern
recalibration be used at all on data with hundreds to thousands of patterns. The abstract's conclusions are not changed (per (d),
and because (b)/(c) apply). Ordering of the table by pattern count is post hoc and is labelled as such.

## Post-hoc comparator (appended 2026-09-04 23:59; referee 5; `results/hcal2/*.csv`, `experiments/score_hcal_switch.py`)

Not registered. A `switch_cv` arm chooses between the global fit and kappa = 0 by the same inner CV. On the four datasets where
kappa = 0 is harmful the switch picks global in every cell and equals it. ACS income: hierarchy (kappa 10-10^3) below the switch in
log-loss on 15/15 cells by 0.0003 (p 6e-5), AUPRC +0.0004. MIMIC-IV regimes, MIMIC-IV first stays, NHANES: hierarchy within
0.00001 of the switch (kappa 10^3-10^4): the global fit under another name. Elsewhere the switch mostly picks kappa = 0 (Higgs 14/15,
Airbnb 11/15) and the hierarchy is within 0.0002 of it. Reading: the safety on three of the four belongs to the cross-validation as
much as to the hierarchy; the paper says so in sec:res-hcal (sentence generated into tables/hcal_switch.tex, then hand-set).
Reproduction: the four registered arms are bit-identical between the two runs on 16 datasets; on NHANES one cell of the kappa = 0
arm differs by 0.0102 AUPRC (seed 2 fold 0; unpenalised per-pattern Platt fit on a small pattern converging differently on
macOS/spinner vs Linux/orca). Tree, global and hierarchical arms are identical there too; the registered kappa = 0 medians are
unaffected beyond that cell.
All 17 comparator runs in (00:10, 2026-09-05): registered arms reproduce to <= 3e-7 on 15 datasets; NHANES as above (kappa = 0,
one cell, 0.010); public_procurement (sweep_42093) kappa = 0 arm differs by up to 1e-3 in one cell for the same reason. Tree,
global and hierarchical arms are identical everywhere. The switch picks kappa = 0 on Higgs, road safety and Airbnb (where
per-pattern recalibration helps) and global elsewhere.
