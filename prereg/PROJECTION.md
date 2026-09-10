# Pre-registration: reduced-panel collapse of the published estimator, and its shrunk test-time projection (APPROVED)

Status: APPROVED by the user 2026-09-03 19:23 ("Approve, freeze and run it"). Written after probe 9 (MIMIC dev half); no holdout record touched before this line.
Approval and a hash in MANIFEST.md freeze it. Companion draft `TRANSPORT.md` is expected to be withdrawn at the
dev stage (eICU probe 8) and is not part of this test.

## Claim under test

C1 (limitation) The published hypergraph estimator predicts the marginal prior for every record whose observed
   set contains no fitted training pattern. When a deployment site stops recording a variable that every training
   pattern contains, this is every record, and the family collapses to AUPRC = prevalence-level.
C2 (fix) Applying the estimator's own shrinkage rule at test time -- fitting the unseen observed-set on the
   training rows that observe it and shrinking toward its immediate ancestors, or toward its nearest fitted
   supersets restricted to its coordinates when it has no ancestors -- removes the collapse at no cost
   in-distribution. Code: `experiments/idea_h_projection.py` (`project_unseen`), committed 13f8a53.

## Dev evidence (MIMIC dev half, probe 9; lab log)

male dropped: 0.110 -> 0.369 (indicator 0.384, unshifted family 0.366); age dropped: 0.110 -> 0.361 (0.378);
four single labs: 0.332-0.343 -> 0.364-0.367 (indicator 0.366-0.383); all six: 0.110 -> 0.350 (0.371);
unit-shift tests unchanged within 0.001. kappa_proj-insensitive over 20-500 -> use the estimator's own kappa.

## Data and design (holdout halves only)

MIMIC-IV holdout half (33,470 records) and eICU holdout half, each split 70/30 stratified (seed 0). Fit once on
the 70 %: tuned mean-imputation LR, tuned indicator LR, HistGradientBoosting, pattern submodels, published
estimator (kappa = median support, min_support 30), projected estimator (same kappa). Test on the 30 % as is
(baseline) and with each of the six most-observed training variables set to missing in turn, then all six at once.
Metric AUPRC; per-drop degradation vs the method's own baseline.

## Predictions

P1 Collapse: for every drop of a variable observed in >= 99 % of training rows, the published estimator's AUPRC
   is within 0.01 of the prevalence-only predictor (AUPRC of a constant), on both datasets.
P2 Recovery: on every drop, the projected estimator is within 0.03 of the tuned indicator and within 0.02 of
   the unshifted family baseline, on both datasets.
P3 No in-distribution change: |projected - published| on the unshifted test <= 0.002, both datasets.
P4 The projected estimator does NOT beat the tuned indicator on any drop by more than 0.005 (stated so the fix
   is not later sold as an accuracy gain).

## Withdrawal

(a) P1 fails -> the limitation is dataset-specific; report as such, keep C2 as an engineering note.
(b) P2 fails on either dataset -> the fix is incomplete; report the failure and the route (ancestors/supersets)
    on which it failed; no claim of recovery.
(c) P3 fails -> the projection changes in-distribution behaviour; it becomes a method change needing its own
    evaluation, not a deployment fix.

## Reporting (Paper 1)

One paragraph in the method section describing the collapse and the projection, one table (drop x method) per
dataset in the supplement, one sentence in limitations. No change to the main-table numbers.

## Outcome (appended 2026-09-03 22:32; scorer `experiments/score_projection.py` on `results/ideas/PROJ/{mimic4,eicu}.csv`)

Run note: the MIMIC half completed 19:33; eICU stalled on a quadratic ancestor lookup in `idea_h_projection.py`
(2.6 h for the baseline row). The lookup was replaced by an equivalent per-set routine (identical on 296 random
lattices), committed 361182a, and both datasets rerun 22:20-22:31. The MIMIC rerun is bit-identical to the first
run (48 rows, max |diff| 0), so the change is a pure speed-up.

held: P1, P3, P4.   failed: P2.   -> withdrawal (b): the fix is incomplete; no claim of recovery.

P1 (collapse) HOLDS on both datasets: dropping `male`, `age`, or all six puts the published estimator and pattern
submodels at exactly prevalence (MIMIC 0.1096, eICU 0.0881).
P3 (no in-distribution change) HOLDS: |projected - published| = 0.0003 (MIMIC), 0.0016 (eICU).
P4 (no accuracy claim) HOLDS: the projection never exceeds the tuned indicator on any drop.
P2 (recovery) FAILS. MIMIC: within 0.03 of the indicator on every drop (0.016-0.026), within 0.02 of the
unshifted family on every single drop (0.001-0.006) but not on all six (0.027). eICU: within 0.02 of the unshifted
family on every single drop (0.003-0.013) and at the boundary on all six (0.020), but 0.036-0.046 below the
indicator on every drop -- because the family is already 0.051 below the indicator in-distribution on eICU
(0.294 vs 0.345), which the indicator clause of P2 did not allow for. Routes: `male`/`age`/all six via nearest
supersets; the four labs via immediate ancestors; both routes show the same residual.

Reading under the pre-registration's own terms: the collapse is real and general; the projection removes it and
returns the family to within 0.001-0.027 of its own unshifted accuracy; it does not close the gap to the tuned
indicator where that gap already existed. Paper 1 reports the limitation, the projection as a deployment
safeguard, the failed prediction and its cause, and nothing more.

Erratum (2026-09-03 23:45): the eICU gap to the indicator in the Outcome above is 0.045-0.055 on every removal (recomputed from results/ideas/PROJ/eicu.csv), not 0.036-0.046. Verdict unchanged.
