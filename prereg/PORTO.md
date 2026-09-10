# Pre-registration: Porto Seguro safe-driver, a diagnostic-flagged non-clinical dataset (APPROVED)

Status: APPROVED by the user 2026-09-04 00:11 ("Approve all, freeze and run them"); drafted 00:06 after the diagnostics-only screen of the development half
(Result 170) and before any comparison on any half. Approval and a hash in MANIFEST.md freeze it.

## Why this dataset

Protocol of 2026-09-04: candidates are screened on their development half with the diagnostics alone and a
flag rule fixed in advance (H_exc >= 0.15, support-30 coverage >= 0.9, iota >= 0.05). Porto Seguro (OpenML
42742; 595,212 policies, 57 variables after dropping the id, prevalence 3.66 %, missing 2.5 % in 82 realised
patterns, missing marked -1 in the release and set to NaN) is the first candidate the rule flags:
H = 2.23 against a permuted-mask null of 1.60 (H_exc = +0.63), coverage 0.998, iota = 0.050, and the tuned
indicator adds +0.0035 AUPRC over tuned mean imputation (0.0566 vs 0.0531) on a 70/30 split of the dev half.

Caveat recorded before the run: the outcome is weakly predictable (AUPRC about 1.5x prevalence). The 0.002
floor is therefore about 4 % of the attainable scale, and every prediction below is small in absolute terms.

## Data and design (holdout half only)

Holdout half by the hash split (`screen_candidates.dev_mask("cand_porto", n)` complement), about 297,600
policies, prevalence expected 3.6 %. Stratified 5-fold cross-validation, seeds 0-2 (15 cells), identical
folds for every arm. Arms: tuned mean-imputation LR; tuned indicator LR; HistGradientBoosting at library
defaults; pattern submodels; hypergraph estimator (kappa = median support, min_support 30, as published);
hypergraph + shrunk projection (same kappa). Permuted-mask null for the estimator and the indicator (mask rows
permuted within the training fold, as in the PLCO nulls). Metric AUPRC; paired within (seed, fold); median
and Wilcoxon; the 0.002 floor.

## Predictions

P1 ours - tuned mean imputation: median >= 0.002, p < 0.05. (The diagnostic's claim.)
P2 ours real - ours null (gain over imputation, real minus permuted): median >= 0.002, p < 0.05.
P3 ours - tuned indicator: median >= 0 (the case the screen's H_exc says the indicator does not capture).
    Honest expectation: this is the prediction most likely to fail; on MIMIC-IV it failed.
P4 ours - pattern submodels >= 0 and ours - projected within 0.002 (no unseen patterns expected: 82
    patterns, coverage 0.998).
P5 The tree at defaults beats every linear arm by >= 0.005 (nonlinearity, as on MIMIC-IV). Stated so a
    tree win is not later read as a pattern effect.

## Withdrawal

(a) P1 fails with ours - imputation <= -0.002: the diagnostic produced a false positive on the first
    dataset it flagged outside medicine; report as such, in the paper, with this file.
(b) P1 holds and P2 fails: the gain is not pattern-structured; report, no claim.
(c) Any within-family inversion (submodels beat ours by >= 0.002): bug hunt before any prose.
(d) P3 fails: the paper's reading stands unchanged (the indicator captures what the pattern carries);
    P1 + P2 alone are reported as "flagged and confirmed against imputation".

## Reporting

One row block in the public-datasets table (Section res-public) and one paragraph in the diagnostic
section; abstract unchanged unless P3 holds, in which case one clause.

## Amendment 2026-09-04 00:38 (before this dataset's holdout run; the earlier run was stopped unread and its partial file deleted, Result 172)

Result 172-173 (Higgs) showed that the published estimator fits each pattern on its support rows and pools
disjoint regimes; a hierarchy fitted on each pattern's OWN rows (experiments/idea_x_exact.py) with kappa
chosen by inner 3-fold CV over {0, 10, 100, 1000, 1e4, 1e5} recovers the gain there. Two arms are added to the
run, with their own predictions; everything above stands unchanged for the published arm.
  exact_submodels  exact-row hierarchy at kappa = 0 (with its permuted-mask null)
  exact_cv         exact-row hierarchy, kappa by inner CV
Dev-half evidence recorded before this run (Result 174):
  Porto dev: exact k=0 0.0571, exact CV (picked 1000) 0.0539; published 0.0538-0.0569; imputation 0.0531; indicator 0.0566.
P7 exact_submodels - tuned imputation >= 0.002 (p < 0.05).   P8 exact_cv - tuned imputation >= 0.002.
P9 exact_submodels - tuned indicator >= 0 (honest expectation: fails or ties; dev +0.0005).
Withdrawal for the added arms: P7 fails with exact_submodels - imputation <= -0.002 -> the exact-row idea does not transfer here; reported.

## Amendment 2026-09-04 00:42 (before any fold of this dataset's run; the 00:38 run was stopped at its header and its file removed)

Result 174 (dev halves): the support-row rule wins on nested patterns (MIMIC dev 0.367 vs exact 0.320) and the
exact-row rule wins on disjoint regimes (Higgs dev 0.708 vs 0.634). One more arm is added:
  family_cv   inner 3-fold CV chooses the fitting rule (support / exact) AND kappa over {0, 10, 100, 1000, 1e4, 1e5}.
P10 family_cv >= max(ours, exact_cv) - 0.002 by paired median (the selection recovers the better rule).
P11 family_cv - tuned imputation >= 0.002 where P1 or P8 holds.

## Outcome (appended 2026-09-04 02:35; `experiments/score_candidate.py cand_porto`, results/cand/cand_porto.csv, 15 cells)

means: indicator 0.0638, interaction 0.0637, tree 0.0627, ours 0.0612 = submodels 0.0612 = family_cv 0.0611, imputation
0.0606, exact_submodels 0.0580, exact_cv 0.0579.
P1 FAILS (ours - imputation +0.0007, p 1e-4: positive, below the 0.002 floor; not <= -0.002, so withdrawal (a) does not
fire). P2 FAILS (real - null excess +0.0010, below the floor). P3 FAILS (indicator ahead by 0.0026). P4 within band.
P5 tie (ours = submodels). P6 FAILS (the tree does not beat the linear arms here: -0.0011). Indicator over imputation
+0.0030 with +0.0032 excess over its null: what pattern signal exists, the indicator captures.
Amended arms: P7 FAILS (exact_submodels - imputation -0.0026) -> withdrawal for the exact-row idea here. P8 FAILS.
P9 FAILS (-0.0059). P10 HOLDS (family_cv = ours, +0.0033 over exact_cv; it chose the support rule in 15/15 cells,
kappa 1e5 in 12). P11 FAILS (+0.0006, below floor).
Reading: the flag was a false positive at this signal level, as the caveat written before the run anticipated
(AUPRC 1.5x prevalence). No arm clears the floor in either direction; the selection mechanism worked. Reported as a
NO WIN row in the sweep 2x2 with its flag.

Erratum (2026-09-04 05:30): "no arm clears the floor in either direction" above is wrong as written: the indicator clears
it upward (+0.0030 over imputation) and the own-rows arms downward (-0.0026, -0.0028). Correct statement: no hypergraph
arm under the support rule clears the floor. Verdict unchanged.
