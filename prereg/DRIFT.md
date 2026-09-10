# Pre-registration: does the missingness lattice detect schema drift that cheaper monitors miss? (APPROVED)

Status: APPROVED by the user 2026-09-05 18:51 ("Approve, freeze and submit the job via nomad"). Drafted 18:40 after the
steering probe (Result 194, `prereg/STEER.md`, drift). No holdout stream has been scored beyond the 6,000-record NHANES pipeline
smoke test recorded below. Runner `experiments/drift_probe.py`, scorer `experiments/score_drift.py`, both committed before the
first run; approval and the hash in MANIFEST.md freeze this file.

## Why the dev result does not count

The steering probe dropped a well-observed variable and found the unfitted share (the share of scored records whose observed set
matches no fitted training pattern) firing in the first window on 32 of 32 cases, while the tree's prediction-shift statistics
needed two or more windows or never fired. That test could not have failed. Removing a column changes the observed set of every
record, so a statistic computed from the observed set must move, and the comparators were prediction statistics, which is the
wrong family. Nothing about the hypergraph was tested.

The question worth asking is whether the lattice sees a drift that the obvious cheap monitor does not: **the missingness rate of
each column, watched separately**. That monitor catches a dropped or sparsified variable just as fast and needs no hierarchy. The
lattice can only earn its place on drift in the *joint* structure, where the marginals hardly move. This registration is built
around that case and around a false-alarm-controlled comparison, so the interesting prediction can lose.

## Statistics under test

L1 unfitted share: fraction of the window's records whose observed set is not a fitted training pattern (fitted = realised in
   training with support >= 30, the estimator's own rule).
L2 pattern-mix divergence: total variation between the window's distribution over fitted patterns (plus one "unfitted" cell) and
   the training distribution over the same cells.
Comparators, given exactly the same calibration and threshold treatment:
C1 per-column missingness monitor: the largest standardised deviation, over columns, of a column's missingness rate. This is the
   monitor the lattice must beat somewhere.
C2 tree prediction mean shift; C3 tree prediction two-sample KS statistic against a reference window (the STEER comparators,
   kept so the two families can be compared on one axis).

## Drift families injected into the scored stream

Joint-structure drift, where C1 is near-blind by construction:
  S3 decouple. Two columns that are co-observed in >= 90 % of training records become mutually exclusive: in each post-drift
     record exactly one of the two is recorded, chosen at random. Each column's own missingness rate moves from about 0.05 to
     about 0.50, so C1 is NOT blind here; the sharper variant S3b keeps each column's rate fixed at its training value by
     recording one of the two in a proportion matched to the pair's marginals, so no column's rate moves by more than 0.05 while
     every affected record carries a pattern the training data never held. **S3b is the discriminating case.**
Marginal drift, where C1 should be as fast as L1 (included so the claim cannot rest on them):
  S1 drop: a well-observed column stops being recorded. S2 sparsify: a well-observed column's recording rate falls to 0.2.
Value-only drift, where L1 and L2 cannot move at all, being functions of the mask:
  D1 covariate shift (+1 SD on three observed columns), D2 prevalence shift (resample to double the positive rate), D3 unit
  change (one column multiplied by 10).
N0 no drift: windows drawn from the same stream, used for calibration and for the false-alarm rate.

## Data and design

The eight datasets of `prereg/STEER.md` (sweep_42739, mimic4, cand_acs_income, cand_nhanes, cand_mimic4_regime, cand_higgs,
cand_airbnb, cand_porto), holdout halves. These holdout halves already carry the sweep and HCAL results; the quantity here
(detection delay) is not a quantity either of those reports, and the reuse is declared rather than hidden. Model: the fixed tree
of `prereg/HCAL.md` (depth 3, rate 0.03, 500 iterations, min leaf 100), fitted once per dataset on a training segment that is
never scored. Windows of 500 records, except NHANES, whose holdout half holds 14,715 records and uses windows of 250. Per drift
family: 20 pre-drift windows then 20 post-drift windows, three seeds. Thresholds
are set per statistic per dataset on 500 bootstrap N0 windows drawn from a held-apart calibration segment, at a common
false-alarm rate of 1 per 100 windows; every statistic is compared at that same rate, so a jumpy statistic cannot buy speed with
false alarms. **A statistic fires when it crosses its threshold in two consecutive windows**, and the detection delay is the
first window of that pair, or "never" within 20. Alongside each run: the tree's AUPRC on each window, so a detection can be
judged against whether the drift cost anything. Each holdout half is subsampled to at most 200,000 records (generator seed 0)
and split 50 / 20 / 30 into the training, calibration and scored segments.

The persistence rule was added on 2026-09-05 at 19:05, before this registration was frozen, after a pipeline smoke test on a
6,000-record NHANES slice (one seed, no outcome read beyond the pipeline's own printout). At a per-window rate of 1 in 100, a
20-window block throws a spurious crossing about 18 % of the time, and in the smoke test the no-drift control duly "detected" at
window 8 and a value-only drift at window 0. Requiring two consecutive crossings takes a block's false-alarm rate to about
0.002 and costs a real detection at most one window, since a real drift persists and a false alarm does not. Without it, P1 and
P3 would have measured noise.

## Predictions

P1 (the discriminating one) On S3b, at the common false-alarm rate, L1 or L2 fires within 1 window while C1 does not fire within
   20, on at least 6 of the 8 datasets. Two ways this loses, both live: C1 may move more than expected because forcing one of a
   pair to be missing shifts each column's rate a little even when the pair's marginals are matched; and L1 may stay flat on a
   dataset whose training data already realised the decoupled combinations, so the new records land on fitted patterns. P4 names
   a third.
P2 On S1 and S2, L1 and C1 both fire at delay 0 on at least 6 of 8; that is, the lattice does NOT beat the cheap monitor on
   marginal drift, and the paper will not claim it does.
P3 On D1--D3, L1 and L2 never fire within 20 windows on 8 of 8 (they are mask functions, so this is a sanity check on the
   pipeline, not evidence), while the tree's own AUPRC falls by at least 0.02 on at least 4 of 8 datasets under D1 or D2. This
   states the limitation in the same breath as the claim: the lattice is blind to the drift that hurts most often.
P4 (declared failure) On datasets whose baseline unfitted share exceeds 0.5, L1 fails to detect S3b, because the statistic is
   saturated before any drift arrives. The baseline shares were measured from the holdout masks alone before writing this line,
   using no outcome and no model, purely to size the design: sweep_42739 0.31, mimic4 0.21, ACS income 0.01, NHANES 0.31,
   MIMIC-IV regimes 0.58, Higgs 0.00, Airbnb 0.00, Porto 0.00. So P4 names MIMIC-IV regimes in advance, and eICU regimes too if
   it is added (its dev coverage was 0.20). Stating this now stops a saturated dataset being explained away afterwards.
P5 At the calibrated threshold, the measured false-alarm rate on fresh N0 windows is at most 3 per 100 for every statistic on
   every dataset.

## Withdrawal

(a) P1 fails -> the lattice statistic is redundant with a per-column missingness monitor. Report as a negative, keep only
    checklist item (1), which is about coverage of the prediction rule and makes no detection claim, and add one sentence to the
    discussion saying the hierarchy adds nothing to drift monitoring.
(b) P5 fails -> the calibration is broken and no comparison between statistics is valid; fix the calibration and re-run before
    reading anything else. Any reading of P1--P4 taken before P5 holds is void.
(c) P3's second clause fails (the value drifts cost less than 0.02 AUPRC) -> the limitation cannot be stated as written; report
    the measured cost instead of the claim.
(d) L1 fires on N0 more often than C1 at the same nominal rate -> the lattice is the noisier monitor; report that alongside any
    P1 result.

## Reporting (Paper 1)

If P1 holds: one paragraph in the discussion beside the deployment checklist, one small table (dataset x drift family x
statistic, delays at a common false-alarm rate), one new checklist line naming the joint-structure case, and one sentence in the
limitations carrying P3. No change to the abstract: this is a monitoring result, and the abstract's conclusions are about
prediction. If P1 fails: one sentence in the discussion, as with Results 187, 189, 191 and 194.

## Outcome (appended 2026-09-05 20:55; `results/drift/*.csv`, scorer `experiments/score_drift.py`; all 8 datasets, 3 seeds each, run on Linux workers)

**P1 FAILS, 0 of 8. Withdrawal (a) applies: the lattice statistic is redundant with a per-column missingness monitor, and no
detection claim is made for the hypergraph.** On the discriminating S3b drift the lattice fires at delay 0 on all 8 datasets --
and so does C1, on all 8. The registration's first named failure route is what happened: forcing one of a co-observed pair to be
missing in 10 % of records moves each column's own rate by about 5 percentage points, and at 500 records per window that is
several standard errors, so C1 is never blind. Holding the marginals tighter would shrink the novel-pattern share by the same
factor, so there is no practical window on these datasets in which the lattice sees something the marginals do not.

P2 HOLDS 8/8 (both fire at delay 0 on S1 and S2), as registered: the lattice does not beat the cheap monitor on marginal drift.
P3 FAILS as written, in an informative way. The lattice never fires on the pure value drifts: 0 of 48 (dataset, seed) cells for
   D1 and D3, both statistics -- it is exactly as blind to value drift as a mask function must be. The 5 of 8 "misses" are all
   D2, the prevalence shift, which is not value-only: resampling to double the positive rate changes which records are in the
   window, and because missingness is informative in these data the pattern mix moves with it. L2 fires on D2 on 7 of 8, and so
   does C1 on 7 of 8. Second clause FAILS 3/8 (needed 4): the value drifts cost the tree >= 0.02 AUPRC on only three datasets,
   so withdrawal (c) applies and the measured cost is reported instead of the stronger limitation sentence.
P4's declared failure DID NOT OCCUR. MIMIC-IV regimes, named in advance as saturated (baseline unfitted share 0.581), detected
   S3b at delay 0 in two of three seeds. Saturation at that level does not blind the statistic; the prediction was wrong.
P5 HOLDS 8/8 (measured false-alarm rate 0.000--0.030 against an allowance of 0.03), so the comparison is valid.
Withdrawal (d) does not apply: pre-drift false alarms are 1 for the lattice and 1 for the per-column monitor over 8 datasets x
8 families x 3 seeds, so neither is the noisier monitor.

Reading: the lattice statistic is a correct schema-drift detector and a useless one, because the cheapest possible monitor is
just as fast on every drift that moves the mask, and neither sees the drift that moves only values. The last open route from the
steering night is closed. Per the reporting rule above, this gets one sentence in the discussion.
