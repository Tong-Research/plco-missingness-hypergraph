# Pre-registration: ACS 2018 income with skip-logic missingness, a diagnostic-flagged non-clinical dataset (APPROVED)

Status: APPROVED by the user 2026-09-04 00:11 ("Approve all, freeze and run them"); drafted 00:20 after the diagnostics-only screen of the development half
(Result 170) and before any comparison on any half. Approval and a hash in MANIFEST.md freeze it.

## Why this dataset

American Community Survey 2018 1-Year person file, ten states (CA, TX, NY, FL, PA, IL, OH, GA, NC, MI),
respondents aged 16+, n = 1,420,339, 43 raw variables kept with their skip-logic blanks (hours worked,
occupation, industry, commute apply only to workers; fertility to women 15-50; field of degree to graduates;
etc.), every income and insurance column dropped. Target: total personal income above 50,000 (prevalence
26.8 %). Missing means "does not apply", and the groups it defines (non-workers, students, retirees) have
different relationships between the remaining variables and income. Screen on the dev half (60,000):
iota 0.338, coverage 0.925, H 1.04 against a permuted-mask null of 0.55 (H_exc = +0.48), tuned imputation
0.7375 vs tuned indicator 0.7477 (+0.0102). FLAGGED by the rule fixed in advance. A first screen with a
public-coverage target was invalid (insurance columns leaked the target) and is recorded as such.

## Data and design (holdout half only)

Holdout half by the hash split (complement of `screen_candidates.dev_mask("cand_acs_income", n)`),
subsampled to 200,000 records (seed 0) for cost, 1,723 realised patterns in the full data. Stratified 5-fold
cross-validation, seeds 0-2 (15 cells). Arms and nulls as in prereg/HIGGS.md. Metric AUPRC; paired within
(seed, fold); 0.002 floor.

## Predictions

P1 ours - tuned mean imputation >= 0.002 (p < 0.05).
P2 ours real - ours null (gain over imputation, real minus permuted) >= 0.002 (p < 0.05).
P3 ours - tuned indicator >= 0.005 (the positive-result bar; expected to be harder here than on Higgs
    because 950 patterns with coverage 0.925 leaves more of the family's mass in small patterns).
P4 ours - mask interaction within +-0.005.
P5 ours - pattern submodels >= 0 (here kappa should matter: many small patterns).
P6 The tree beats every linear arm by >= 0.02.

## Withdrawal: as prereg/HIGGS.md (a)-(e).

## Reporting: as prereg/HIGGS.md.

## Amendment 2026-09-04 00:38 (before this dataset's holdout run; the earlier run was stopped unread and its partial file deleted, Result 172)

Result 172-173 (Higgs) showed that the published estimator fits each pattern on its support rows and pools
disjoint regimes; a hierarchy fitted on each pattern's OWN rows (experiments/idea_x_exact.py) with kappa
chosen by inner 3-fold CV over {0, 10, 100, 1000, 1e4, 1e5} recovers the gain there. Two arms are added to the
run, with their own predictions; everything above stands unchanged for the published arm.
  exact_submodels  exact-row hierarchy at kappa = 0 (with its permuted-mask null)
  exact_cv         exact-row hierarchy, kappa by inner CV
Dev-half evidence recorded before this run (Result 174):
  ACS dev: exact k=0 0.7097, exact CV (picked 100) 0.7290; published 0.7353; imputation 0.7375; indicator 0.7477.
P7 exact_cv - tuned imputation: honest expectation NEGATIVE (dev -0.009); prediction: median <= 0. Stated so that
   a positive result here cannot be claimed as predicted.  P8 exact_cv >= exact_submodels by >= 0.005 (dev +0.019:
   on 950 nested patterns shrinkage helps the exact-row hierarchy).  P9 published - exact_cv >= 0 (dev +0.006).
Reading rule: on nested survey patterns the exact-row hierarchy is expected to lose to both the published
estimator and imputation; the positive case is Higgs-shaped (few disjoint regimes), and ACS tests the boundary.

## Amendment 2026-09-04 00:42 (before any fold of this dataset's run; the 00:38 run was stopped at its header and its file removed)

Result 174 (dev halves): the support-row rule wins on nested patterns (MIMIC dev 0.367 vs exact 0.320) and the
exact-row rule wins on disjoint regimes (Higgs dev 0.708 vs 0.634). One more arm is added:
  family_cv   inner 3-fold CV chooses the fitting rule (support / exact) AND kappa over {0, 10, 100, 1000, 1e4, 1e5}.
P10 family_cv >= max(ours, exact_cv) - 0.002 by paired median (the selection recovers the better rule).
P11 family_cv - tuned imputation >= 0.002 where P1 or P8 holds.

## Outcome (appended 2026-09-04 03:04; `experiments/score_candidate.py cand_acs_income`, results/cand/cand_acs_income.csv, 15 cells on a 200,000 holdout subsample)

means: tree 0.8106, exact_cv = family_cv 0.7477, interaction 0.7474, indicator 0.7473, ours 0.7382 (projected 0.7385),
submodels 0.7383, exact_submodels 0.7377, imputation 0.7368.
Published arm: P1 FAILS (+0.0011, below floor); P2 HOLDS (real - null +0.0111); P3 FAILS (indicator +0.0094 ahead);
P4 outside; P5 tie; P6 tree +0.063 over the best linear arm. Indicator over imputation +0.0107, null excess +0.0109.
Amended arms: P7 -- I predicted exact_cv - imputation <= 0 and it is +0.0104 (p 6e-5). By this file's own rule a
positive result here is UNPREDICTED and is reported as such, not as a confirmation. P8 HOLDS (+0.0096: shrinkage
helps the exact-row hierarchy on nested survey patterns). P9 FAILS (published - exact_cv -0.0098: the exact hierarchy
beats the published one). P10 HOLDS (family_cv chose ('exact', 100) in 15/15; = exact_cv). P11 HOLDS (+0.0104).
family_cv - indicator +0.0005 (p 0.28): a tie with the tuned indicator. Exact real - null excess +0.0574.
Reading: on nested skip-logic patterns the CV-selected hierarchy matches the best linear comparator and beats
imputation by a full hundredth; it does not beat the indicator. The exact-row rule's win here was not predicted
from the dev half (where it lost to imputation by 0.009), so the boundary between the two fitting rules is not yet
understood and must not be stated as understood.
