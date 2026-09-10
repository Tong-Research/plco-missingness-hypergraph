# MISDIAG: confirmation, on fresh seeds, that an institutional regime manufactures false detections (registered 2026-09-07 00:15)

## What is already seen, and disclosed

Replicates 0 to 19, run under the corrected `causal-learn` 0.1.4.7, gave the following means for the number of
indicators MVPC's Step 1 reports a parent for, out of twelve:

| regime strength | aligned mask | closed-missingness control |
|---|---|---|
| 0 | 1.20 | 0.85 |
| 1 (realistic) | 5.55 | 0.60 |
| 2 | 6.45 | 1.30 |

The thresholds below were chosen with those numbers in view. This is therefore a confirmation on data not yet seen,
not a blind test: it runs replicates 20 to 39, whose seeds have never been used, with everything else identical.

## Design

`experiments/probe_mvpcdet.py`, unchanged, replicates 20 to 39, under the pinned `causal-learn==0.1.4.7`. Same eICU
substrate, same twelve columns, same regime anchored at 0.184, same closed-missingness control, same secondary
self-masking condition.

## Predictions

M1. At the realistic regime strength with the aligned mask, the mean number of indicators reported with a parent is
    at least 3.0.
M2. Under the closed-missingness control at the same strength, it is at most 1.5.
M3. The difference between them is at least 3.0 indicators.
M4. The difference is larger at twice the regime strength than at zero.
M5. At zero regime strength the aligned and control means differ by at most 1.0, since there is then no regime for
    the mask to be aligned with.

## Withdrawal

(a) M1 or M3 fails: the effect does not reproduce on fresh seeds and nothing is claimed. Paper B keeps the second
    negative result as written.
(b) M2 fails: the control is not clean, and the comparison cannot support the claim.
(c) M5 fails: something other than the regime differs between the aligned and control conditions, and the design is
    not isolating what we think it is.

## Outcome (2026-09-07 00:15; 20 fresh replicates, seeds 20-39, causal-learn 0.1.4.7; scorer `experiments/score_misdiag.py`)

**All five predictions hold on seeds never used before.**

M1: 4.65 of twelve indicators reported with a parent under the aligned mask at the realistic regime strength.
M2: 0.90 under the closed-missingness control. M3: a difference of 3.75. M4: the difference grows from -0.10 at zero
regime strength to 5.70 at twice realistic. M5: at zero strength the two conditions differ by 0.10, as they must,
since there is then no regime for the mask to be aligned with.

The effect is confirmed. MVPC's Step 1, in the implementation its own authors wrote and with the library's regression
removed, reports value-driven missingness that does not exist, in proportion to the strength of an institutional
ordering regime, and only when the record's mask is aligned with that regime. The transplanted mask is independent of
the simulated variables within a hospital by construction, so every one of these detections is a false positive.

A note on the secondary condition. With partial self-masking added, so that there is something real to find, the
aligned and control conditions give 7.90 and 7.45. The step finds the real signal in both, and the regime's
contribution is no longer separable there. That is expected and is not evidence against the main result, but it does
mean the claim is about detection under a regime and not about detection in general.
