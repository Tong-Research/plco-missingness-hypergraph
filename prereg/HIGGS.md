# Pre-registration: ATLAS Higgs, a diagnostic-flagged non-clinical dataset (APPROVED)

Status: APPROVED by the user 2026-09-04 00:11 ("Approve all, freeze and run them"); drafted 00:10 after the diagnostics-only screen of the development half
(Result 170) and before any comparison on any half. Approval and a hash in MANIFEST.md freeze it.

## Why this dataset

ATLAS Higgs ML challenge (OpenML 45550; 818,238 simulated events, 30 variables after dropping id and
weights, signal prevalence 34.3 %). Jet-dependent variables are undefined (-999, set to NaN) when the event
has fewer jets, and the invariant-mass variable is undefined when it cannot be computed: missing means
"does not apply", the six realised patterns are physical regimes, and the relationships between the
remaining variables and the label differ by regime. Screen on the dev half (60,000): iota 0.151, coverage
1.000, H 0.81 against a permuted-mask null of 0.10 (H_exc = +0.70), tuned imputation 0.6722 vs tuned
indicator 0.6794 (+0.0072). FLAGGED by the rule fixed in advance (H_exc >= 0.15, cov30 >= 0.9, iota >= 0.05).
This is the regime the synthetic suite says the method wins in: few, large, heterogeneous patterns.

## Data and design (holdout half only)

Holdout half by the hash split (complement of `screen_candidates.dev_mask("cand_higgs", n)`), about
409,000 events. Stratified 5-fold cross-validation, seeds 0-2 (15 cells), identical folds for every arm.
Arms: tuned mean-imputation LR; tuned indicator LR; tuned mask-interaction LR (indicator x features, the
linear model that can represent pattern-specific slopes); HistGradientBoosting at library defaults; pattern
submodels; hypergraph estimator (kappa = median support, min_support 30, as published); hypergraph + shrunk
projection. Permuted-mask null for the estimator, the indicator and the interaction model. Metric AUPRC;
paired within (seed, fold); median and Wilcoxon; 0.002 floor.

## Predictions

P1 ours - tuned mean imputation >= 0.002 (p < 0.05).
P2 ours real - ours null (gain over imputation, real minus permuted) >= 0.002 (p < 0.05).
P3 ours - tuned indicator >= 0.005: the positive result the paper lacks -- the pattern carries slope
    information an indicator cannot represent. This is the prediction that matters.
P4 ours - mask interaction: median within +-0.005 (the interaction model can represent the same slopes;
    with six patterns and ~65,000 rows each, shrinkage should neither help nor hurt much).
P5 ours - pattern submodels: median within +-0.002 (large supports; kappa acts weakly).
P6 The tree beats every linear arm by >= 0.02 (the physics is nonlinear). Stated so it is not read as a
    pattern effect; the pattern effect is P3 minus nothing.

## Withdrawal

(a) P1 fails with ours - imputation <= -0.002: false positive of the diagnostic; report in the paper.
(b) P1 holds, P2 fails: not pattern-structured; report, no claim.
(c) Submodels beat ours by >= 0.002: bug hunt first.
(d) P3 fails (ours - indicator < 0.005): no positive claim beyond "beats imputation where flagged"; the
    abstract's practitioner rule stands. If ours - indicator < 0: the indicator wins again, reported.
(e) P4 fails with the interaction model ahead by > 0.005: the win is representational, not hierarchical;
    reported as such (the interaction model is the cheaper way to get it).

## Reporting

If P1-P3 hold: one paragraph in the diagnostic section, one row block in the public table, one sentence in
the abstract's results ("on a dataset the diagnostic flagged outside medicine the estimator beat both
imputation and the indicator") and the conclusions' rule gains its positive branch. Otherwise as (a)-(e).

## Outcome (appended 2026-09-04 00:26; scorer `experiments/score_candidate.py cand_higgs`, results/cand/cand_higgs.csv, 15 cells)

means: tree 0.8505, indicator 0.6759, interaction 0.6757, imputation 0.6681, submodels 0.6416, ours 0.6368, projected 0.6368.
P1 FAILS: ours - imputation -0.0313 (p 6e-5) -> withdrawal (a): a false positive of the diagnostic for the estimator AS PUBLISHED.
P2 HOLDS: real - null excess +0.0057 (p 6e-5): the pattern structure is real; the estimator loses it.
P3 FAILS: ours - indicator -0.0391. P4 outside (-0.0389). P5 INVERSION: submodels ahead of ours by 0.0048 -> bug hunt
(c). P6 tree +0.175 over the best linear arm. Indicator - imputation +0.0078, excess over null +0.0077.
Bug hunt (Result 172, dev half, done before this outcome was scored): not a bug. Both the estimator and the
pattern-submodels baseline fit each pattern on its SUPPORT rows (every row observing the pattern's variables);
on six disjoint jet regimes this pools regimes, and the estimator's support-weighted combine over all applicable
patterns then adds further pooling, which is why it sits below submodels. A model fitted on each pattern's OWN
rows reaches 0.708 on the dev half (kappa = 0 on the exact-row hierarchy), +0.044 over imputation.
Reading under this file's terms: the estimator as published fails here; the hypothesis that the pattern pays is
supported (P2, and the exact-row result on the dev half). Any claim for an exact-row variant requires its own
pre-registration on data this run did not touch (amendment to follow).

## Amendment 2026-09-04 00:38: exact-row arms on an untouched slice of the DEV half

The holdout half is spent (Outcome above). The dev half (409,119 events) was touched only through three fixed
subsamples: the screen (60,000, rng seed 0 over the dev index), the diagnosis (120,000, rng seed 0), and the
kappa path (60,000, rng seed 1). The complement of their union (about 250,000 events) has not been read by
any analysis and is declared the test slice for the added arms; `experiments/run_candidate.py --npz cand_higgs
--slice dev-remainder` reproduces it. Design and arms as in the amendment to PORTO.md (3 x 5 cells).
Predictions: P7 exact_submodels - tuned imputation >= 0.02 (dev diagnosis +0.044). P8 exact_submodels - tuned
indicator >= 0.005 (the positive bar; dev +0.035). P9 exact_cv within 0.005 of exact_submodels (CV picks
kappa = 0 on the dev subsample). P10 exact_submodels real - null excess >= 0.01.
Withdrawal: P7 fails -> the dev-half gain does not replicate; no claim. P8 fails with P7 holding -> "beats
imputation where flagged, not the indicator" as for MIMIC-IV.

## Outcome of the 00:38 amendment (appended 2026-09-04 00:49; results/cand/cand_higgs.devrem.csv, 15 cells on the 247,096-event untouched dev slice)

means: tree 0.8514, exact_cv 0.7139 = exact_submodels 0.7139, indicator 0.6780, interaction 0.6778, imputation 0.6698,
submodels 0.6415, ours 0.6365. P7 HOLDS (+0.0441, p 6e-5). P8 HOLDS (+0.0356, p 6e-5): the positive bar is cleared.
P9 HOLDS (exact_cv picks kappa = 0 in every cell; difference 0). P10 HOLDS (real - null excess +0.0451).
Also: exact - interaction +0.0357 (a linear model that can represent pattern-specific slopes still loses);
tree - exact +0.138 (P6 of the original file: nonlinearity dominates and is not a pattern effect).
Reading: on a dataset the diagnostic flagged, whose patterns are few disjoint regimes, conditioning on the pattern
pays and neither the indicator nor the interaction expansion captures it; the published estimator's support rule
loses the gain (-0.034 vs imputation, Result 173), the exact-row hierarchy keeps it.

## Amendment 2026-09-04 14:50: the cross-validated arms on the HOLDOUT half (so the table row can be holdout-only)

The holdout half has been scored for the published arm (Outcome above) but never for the own-rows or cross-validated
arms; the dev-slice replication (Result 175) predicts them. Prediction, written before the run: on the holdout half,
exact_cv - tuned imputation in [0.035, 0.055] and exact_cv - tuned indicator in [0.025, 0.045] (paired medians, 3 x 5),
family_cv chooses the own-rows rule with kappa <= 100 in >= 12 of 15 cells. If both intervals hold, the sweep table's
Higgs row moves to the holdout and loses its double dagger; if not, the slice row stays and the discrepancy is reported.
Dispatched to dugong.

## Outcome of the 14:50 amendment (appended 2026-09-04 16:20; results/cand/cand_higgs.csv rerun with every arm on the HOLDOUT half, 15 cells, dugong)
exact_cv - tuned imputation +0.0434 (predicted [0.035, 0.055]) HOLDS; exact_cv - tuned indicator +0.0355 (predicted
[0.025, 0.045]) HOLDS; family_cv = exact_cv (+0.0434 over imputation; own-rows rule chosen); exact_cv - interaction +0.0357.
The table's Higgs row therefore moves to the holdout half and loses its double dagger; the dev-slice result (Result 175)
stands as the pre-registered replication that predicted it.
