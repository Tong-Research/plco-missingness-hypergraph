# MVPCDET: the instrumented detection step (pre-registered 2026-09-06 22:30)

Result 215 (prereg/PLASMODE.md) found that an institutional missingness regime makes a diagnostic detect value-driven
missingness that does not exist, at every one of twenty replicates. That was measured with a stand-in for the
detection step rather than the algorithm's own. This registers the instrumented rerun.

## What is already known, and disclosed

The stand-in result is known and is the reason this experiment exists: with the aligned transplanted mask and no
self-masking, the stand-in flagged a mean of 5.15 columns of twelve at the realistic regime strength and 10.45 at
twice that, against 0.05 and 0.00 under the closed-missingness control, with at least one column flagged in 100% of
replicates at realistic strength. The predictions below were written after seeing those numbers. They are therefore
not a blind test of whether a regime produces spurious detections; they are a test of whether MVPC's own step behaves
as our stand-in did, which is the question a referee will ask.

## Design (`experiments/probe_mvpcdet.py`)

Identical substrate, replicate seeds, regime strengths and conditions to prereg/PLASMODE.md: eICU rows from hospitals
with at least 500 stays, the real missingness of twelve fixed columns, a random graph over twelve linear Gaussian
variables, a latent regime with four children whose means shift by `gamma * 0.184 * delta`, gamma in {0, 1, 2}, the
aligned mask against the closed-missingness control, a secondary self-masking condition at gamma = 1, and twenty
replicates.

The measurement is `get_parent_missingness_pairs`, which is Step 1 of `mvpc_alg` in causal-learn, called with the same
arguments the algorithm uses. Recorded per cell: the number of indicators for which it reports at least one parent,
the total number of reported parent-indicator pairs, and the share of reported parents that are regime-affected,
meaning the children of the regime and all their descendants in the generating graph, since only those carry the
hospital-dependent shift. The stand-in is recomputed alongside for direct comparison.

## Predictions

Q1. At gamma = 1 with the aligned mask, at least one indicator is reported to have a parent in at least 90% of
    replicates.
Q2. At gamma = 1 with the aligned mask, the mean number of indicators reported to have a parent is at least 3.0.
Q3. Under the closed-missingness control at gamma = 1, that mean is at most 0.5.
Q4. The mean is non-decreasing in gamma under the aligned mask across 0, 1 and 2.
Q5. At gamma = 1 with the aligned mask, at least 90% of reported parents are regime-affected.

## Withdrawal

(a) Q1 or Q3 fails: the algorithm's own step does not behave as our stand-in did. The misdiagnosis claim is dropped
    from Paper B, and Result 215's P5 is restated as a property of our stand-in only, which is worth little.
(b) Q2 fails while Q1 holds: the effect is real but small; the claim is stated as "at least one column" and the
    quantitative version is dropped.
(c) Q4 fails: the effect is not driven by the regime's strength; the mechanism sentence is withdrawn.
(d) Q5 fails: the spurious parents are not the variables the regime touches, so our explanation of the mechanism is
    wrong; the finding stands, the explanation does not.

## Disclosure (appended 2026-09-06 22:35, after the freeze, before the farm run)

One replicate was run on dugong. Its numbers were seen before the farm run and the predictions above were NOT edited,
although they are now very likely to fail, and the honest thing is to record that here rather than to redesign.

In that replicate MVPC's own detection step reported that ALL TWELVE indicators have at least one parent, in EVERY
condition: at regime strength zero, at realistic strength, at twice realistic strength, and under the
closed-missingness control, which is exactly missing completely at random with respect to the simulated variables.
The number of reported parent-indicator pairs ranged only from 34 to 37 across all eight cells. Our stand-in, computed
on the same data, gave 0, 3 and 7 under alignment and 0, 0 and 1 under the control, reproducing Result 215.

If this holds across replicates then Q3 and Q4 fail and withdrawal (a) applies: the algorithm's own step does not
behave as our stand-in did, and the misdiagnosis claim comes out of Paper B. The apparent reason is that Step 1 has
no specificity at this sample size, reporting parents for every indicator even under data that are missing completely
at random. That would be a finding about the algorithm rather than about the regime, it is not what this file
registers, and it must not be claimed from this run. Whether it is driven by sample size is a separate question that
needs its own registration, sweeping n, before anything is said about it.

The run proceeds as registered so that the failure is documented on twenty replicates rather than one.

## Outcome (2026-09-06 22:25; 20 replicates, 0 failures; scorer `experiments/score_mvpcdet.py`)

**Q3 FAILS and withdrawal (a) applies. The misdiagnosis claim comes out of Paper B.**

The instrumented step reports parents for a mean of 11.65 of the twelve indicators, and it reports the same 11.65
under the closed-missingness control, which is missing completely at random with respect to the simulated variables.
The count is flat across regime strengths, 11.65, 11.65 and 11.75, and the number of reported parent-indicator pairs
varies only between 33.4 and 34.2 across all six cells. Q1, Q2 and Q4 pass, but they pass trivially: they are
satisfied by a step that reports parents for everything. Q5 passes at 0.966 against a base rate of 0.94, so it carries
almost no information and is not evidence for the mechanism.

Our stand-in, computed on the same data in the same script, behaved as Result 215 reported: 0.10, 5.15 and 10.45 under
alignment against 0.00, 0.15 and 0.05 under the control. So the two measurements genuinely differ, and the algorithm's
own step is the one that matters.

**What this costs.** Result 215's P5 is hereby restated as a property of our stand-in and not of MVPC. The claim that
an institutional regime makes the published diagnostic misidentify the mechanism is withdrawn. Paper B loses the plank
that its fourth revision was built on.

**What must not be claimed from this run.** The step reports parents for essentially every indicator even under data
that are missing completely at random. If that is right it is a more serious observation than the one we set out to
make, but this experiment was not designed to establish it: there is no sample-size sweep, no comparison against the
step's nominal error rate, and no check of whether the behaviour is specific to this implementation, this test or this
number of variables. It needs its own pre-registration before a word is written about it.

## Amendment 1 and re-run (2026-09-07 00:05)

The instrumented step used `causal-learn` 0.1.4.8, which `papers/MVPC-SPEC-VS-CODE.md` shows carries a one-line
regression making Step 1 profile the variable rather than its missingness indicator. The numbers above are therefore
not evidence about MVPC and must not be reused as such. The recorded conclusion, that the misdiagnosis claim comes out
of Paper B, is unaffected, because it rested on the instrumented step differing from our stand-in and that difference
is now explained rather than removed.

The fleet is pinned to 0.1.4.7 and this experiment is being re-run unchanged at twenty replicates, to establish what
the corrected step does under the transplanted mask. No prediction is registered for the re-run: after the spec
report the outcome is largely foreseeable, and pretending otherwise would be worse than saying so.

## Re-run outcome (2026-09-07 00:10; 20 replicates under the pinned causal-learn 0.1.4.7)

No prediction was registered for this re-run, so what follows is descriptive.

With the corrected library, the instrumented step reports parents for a mean of 5.55 of twelve indicators under the
aligned transplanted mask at the realistic regime strength, against 0.60 under the closed-missingness control, and
6.45 against 1.30 at twice the regime strength. At zero regime strength the two are 1.20 and 0.85. Our stand-in gave
5.15 against 0.10 on the same data.

So the misdiagnosis effect is real after all, and the original withdrawal fired because of the library defect rather
than because the claim was false. The step, working correctly, detects value-driven missingness that does not exist,
in proportion to the strength of the institutional regime, and it does so only when the mask is aligned with that
regime.

This must not be claimed from these numbers. The re-run carries no registered predictions and its thresholds would be
chosen after seeing it. A confirmation on fresh replicate seeds is registered separately in `prereg/MISDIAG.md`.
