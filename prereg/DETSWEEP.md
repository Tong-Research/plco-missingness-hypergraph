# DETSWEEP: is MVPC's Step 1, as implemented, calibrated? (registered 2026-09-06 23:50)

## Protocol lapse, recorded first

This file was written AFTER the script had been run on one replicate. That is a departure from the rule this project
works under, which is to freeze predictions before any run, and it is recorded here rather than hidden. What follows
is therefore NOT a blind test. It is a confirmation run of an observation already made, with thresholds written down
so that the confirmation is checkable and so that a failure to reproduce would be visible.

The one-replicate observation, in full:

| mechanism | n = 500 | n = 5,000 | n = 50,000 |
|---|---|---|---|
| indicators reported with a parent, independent MCAR mask | 11/11 | 11/11 | 11/11 |
| indicators reported with a parent, block-dependent MCAR mask | 11/11 | 11/11 | 11/11 |
| indicators reported with a parent, MAR mask | 11/11 | 10/11 | 11/11 |
| false parent-pair rate, independent MCAR | 0.198 | 0.273 | 0.281 |
| share of indicators whose TRUE parent was found, MAR | 0.09 | 0.18 | 0.27 |

## What this tests

MVPCDET found the step reports parents for 11.65 of twelve indicators under a transplanted intensive-care mask and
the same under a control carrying no information. Two explanations were available: sample size, and dependence among
the indicators. This sweeps both, in a fully synthetic setting where the truth is exact.

## Design (`experiments/probe_detsweep.py`)

X from a random linear Gaussian graph over twelve variables. Three mask mechanisms, all leaving one root column always
observed: `mcar_indep`, each indicator drawn independently at rate 0.30, so no dependence among indicators and none
with the variables; `mcar_dep`, indicators drawn in three near-identical blocks, so strong dependence among indicators
but still none with the variables; and `mar`, each indicator driven by the always-observed root, so exactly one true
parent exists. n in {500, 1000, 2000, 5000, 10000, 20000, 50000}, twenty replicates, alpha 0.01, the same call the
algorithm makes.

Under both MCAR mechanisms every reported parent is a false positive. Under MAR the root is the one true parent.

## Predictions

S1. Under `mcar_indep`, the share of indicators reported with a parent is at least 0.90 at every n from 500 to 50,000,
    that is, it does not rise with sample size because it is already saturated at the smallest.
S2. The same holds under `mcar_dep`, and the two mechanisms differ by at most 0.10 at every n: dependence among the
    indicators is not what drives the reports.
S3. The false parent-pair rate under `mcar_indep` exceeds the nominal 0.01 by at least a factor of ten at every n.
S4. Under `mar`, the share of indicators for which the true parent is among those reported is at most 0.50 at every n:
    the step also lacks power to find a parent that is really there.

## Withdrawal

(a) S1 fails: the behaviour is sample-size driven after all, the one-replicate observation did not reproduce, and
    nothing is claimed.
(b) S2 fails: indicator dependence is the driver, which would make this a statement about masks like the clinical one
    rather than about the step in general.
(c) S3 fails: the reports are within a plausible multiple of the nominal level and there is nothing to report.
(d) S4 fails: the step has power, so the finding is about specificity alone and must be stated that way.

## The attribution question, which this experiment cannot settle

Everything here concerns the `causal-learn` implementation. Whether the behaviour follows the algorithm as published,
or is a defect of this implementation, is a question about the paper and the code, not about these runs. No claim
naming the algorithm rather than the implementation may be made until that is checked directly against the published
specification.

## Outcome (2026-09-06 23:50; 20 replicates, 0 failures; scorer `experiments/score_detsweep.py`)

**All four predictions hold, and the one-replicate observation reproduces.**

S1. Under a mask drawn independently of everything, the step reports at least one parent for 96 to 99 percent of
    indicators at every sample size from 500 to 50,000. It is saturated at the smallest sample size tested, so the
    behaviour is not driven by sample size.
S2. A mask whose indicators move in near-identical blocks gives the same, within 0.014 at every n. Dependence among
    the indicators is not the driver either.
S3. The false parent-pair rate runs from 0.190 to 0.270 against a nominal 0.01, nineteen to twenty-seven times the
    level, and it rises slowly with n rather than falling.
S4. When a genuine parent exists, the step recovers it for 0.159 to 0.277 of indicators, so it also lacks power.

The two explanations available after MVPCDET are both excluded. What remains is that the step, as implemented in
`causal-learn`, reports a parent for essentially every missingness indicator whatever the mechanism, and finds the
real parent about a fifth of the time when there is one.

**The attribution question is still open and nothing may be claimed about the published algorithm until it closes.**
A separate check of the published specification against this implementation is under way and is recorded in
`papers/MVPC-SPEC-VS-CODE.md`. Until that returns, this outcome supports statements about the implementation only.

## Amendment 1 and re-run (2026-09-07 00:05)

`papers/MVPC-SPEC-VS-CODE.md` establishes that everything measured above is an artefact of one release. In
`causal-learn` 0.1.4.8, `detect_parent` substitutes the missingness indicator into a copy of the data and then binds
the independence test to the ORIGINAL data, so Step 1 profiles the variable rather than its indicator, and test-wise
deletion removes exactly the rows in which the indicator is one. The line was correct until commit `a160a5df3`
(PR #242, May 2026) and is correct again once restored. The published specification, the first author's own earlier
contribution to the same library, and the authors' R reference implementation all agree with each other and not with
0.1.4.8.

The outcome recorded above is therefore withdrawn as a statement about MVPC. It stands only as a statement about that
one release, and it is retained here as the record of how the artefact was found.

The fleet is now pinned to `causal-learn==0.1.4.7`, recorded in `requirements-pins.txt`, and the experiment is being
re-run unchanged at twenty replicates. The predictions for the re-run are the negations of S1 to S4, since the
diagnostic in the spec-versus-code report suggests the corrected step is calibrated and powerful:

T1. Under independent MCAR, the share of indicators reported with a parent is at most 0.20 at every n.
T2. The false parent-pair rate is at most 0.02 at every n, that is, at or below the nominal level.
T3. Under MAR, the true parent is recovered for at least 0.90 of indicators at every n at or above 1000.
T4. The block-dependent MCAR mask behaves like the independent one, within 0.10 at every n.

If T1 to T3 hold, Result 216 is withdrawn in full and replaced by a statement about the library release. If they fail,
the artefact is not the whole story and the difference must be explained before anything is said.

## Re-run outcome (2026-09-07 00:10; 20 replicates under the pinned causal-learn 0.1.4.7)

T1, T2, T3 and T4 all hold. Under a mask independent of the variables the step reports a parent for 6 to 10 percent
of indicators, the false parent-pair rate is 0.006 to 0.010 against a nominal 0.01, and where a true parent exists it
is recovered for 98 percent of indicators at n = 500 and 100 percent at every larger n. The block-dependent mask
behaves like the independent one.

The step is calibrated and close to perfectly powered. Result 216 is withdrawn in full: there was never anything
wrong with the algorithm, only with one release of one library, and the record now says so.
