# PLASMODE: what does an institutional missingness regime cost causal discovery? (pre-registered 2026-09-06 22:15)

Third design. The first two were discarded after `PAPERB-DUP-SIMULATION.md` and `PAPERB-DUP-ASSUMPTIONS.md` found
three flaws, a missing arm and a naming problem; the flaws and their fixes are recorded in `papers/PAPERB-DESIGN.md`.

## Motivation, in one paragraph

Six published methods for causal discovery or estimation under missing data assume either that no missingness
indicator influences another, or that the indicators have no unmeasured common cause. Our measurements say the
indicators are strongly dependent and that the dependence is a latent class which, on eICU, is the hospital. Holovchak
et al. (Biostatistics 2025) prove that a closed missingness mechanism, in which no path connects the indicators to the
variables, keeps available-case analysis valid even under MNAR, and state that closed missingness is common in
clinical data. This experiment asks what it costs when that is false.

## Design (`experiments/probe_plasmode.py`)

A plasmode simulation with a transplanted missingness mask. Substrate: eICU stays from the 69 hospitals with at least
500 stays, and the real missingness of twelve fixed columns, chosen before any outcome was examined as those with the
largest between-hospital spread in missing rate (lab_24, lab_17, vent_FiO2, vent_LPM_O2, lab_31, lab_32, lab_29,
lab_28, lab_30, lab_22, lab_0, lab_18). 20,000 rows per replicate, 20 replicates.

Truth: a random directed acyclic graph over the twelve variables with eighteen edges, linear Gaussian, plus a latent
root Z, the hospital, with four children. A child of Z has its mean shifted by `gamma * 0.184 * delta[z, j]`, where
0.184 is the measured median between-hospital standard deviation of standardised column means in real eICU, so
gamma = 1 is the realistic level by construction. gamma takes 0, 1 and 2.

Alignment. ALIGNED keeps each row's own mask. The CLOSED-MISSINGNESS CONTROL permutes mask rows across the sample.
This preserves the multiset of mask rows exactly, and therefore every marginal rate, every indicator-indicator
dependence and every per-test deletion sample size, while cutting the path between the mask and the variables. Any
difference between the two arms therefore cannot be a difference of statistical power.

A secondary condition at gamma = 1 adds partial self-masking, in which a column's own high values raise its
missingness, so that MVPC has something real to correct.

Arms: PC on the complete data (the floor); PC with test-wise deletion; MVPC; FCI with test-wise deletion; CD-NOD given
the true hospital identifier; and CD-NOD given a regime estimated from the mask alone by a ten-class Bernoulli
mixture. All are the causal-learn implementations, MVPC being the authors' own.

Scoring is on skeletons. Target A is the true graph over the variables, which every arm should recover and none fully
can; the headline quantity is each arm's excess over the complete-data arm on the same replicate. Target B adds a
clique on the children of Z, which is what a latent-aware method should recover, and is reported for FCI.

## Predictions

P1. At gamma = 1, aligned masks cost more than the closed-missingness control: for test-wise-deletion PC the mean
    excess is at least 1.0 edge higher under alignment, and higher in at least 70% of replicates.
P2. The cost tracks the regime's strength: the aligned-minus-control gap for test-wise-deletion PC is non-decreasing
    across gamma in {0, 1, 2}, and at gamma = 0 it is at most 0.5 edges.
P3. MVPC does not remove it: its aligned-minus-control gap is at least 0.7 times that of test-wise-deletion PC.
P4. A regime estimated from the mask alone removes most of it: CD-NOD with the estimated regime has an
    aligned-minus-control gap at most 0.5 times that of test-wise-deletion PC, and is within 1.0 edge of CD-NOD given
    the true hospital identifier.
P5. Under aligned masks with no self-masking, the premise MVPC corrects for is falsely detected: at least one column
    is flagged as having value-driven missingness in at least 50% of replicates, which is a false positive by
    construction because within a hospital the transplanted mask is independent of the simulated variables.

## Withdrawal

(a) P1 fails: the regime costs nothing measurable for structure learning. The simulation is dropped and Paper B
    becomes an audit paper resting on the measurements already in hand, which is a smaller but still viable paper.
(b) P2 fails: the effect is not driven by the regime's influence on the variables, the mechanism is not what we
    claim, and only the curve is reported.
(c) P4 fails: our proposed remedy does not work, and the paper reports the cost without offering a fix.
(d) P5 fails: the MVPC-specific claim is dropped; P1 to P4 are unaffected.

## Registered in advance

The twelve columns, the anchor 0.184, the graph size, the sample size, the number of replicates, the significance
level 0.01 and the arm list are all fixed above and were fixed before the script was run on anything.

## Disclosure (appended 2026-09-06 22:25, after the freeze, before the farm run)

One replicate was run on dugong to check the script executes. Its numbers were seen before the farm run and the
predictions were not edited. Skeleton distances to target A: complete data 1 to 3 edges of 18, every other arm 3 to 6,
with the aligned-minus-control difference at 1, 0 and 1 edge for gamma 0, 1 and 2 respectively, which is within the
noise of a single replicate and gives no information about P1 to P4. The spurious-detection count was 0 at gamma 0,
3 at gamma 1 and 7 at gamma 2 under alignment, and 0 under the closed-missingness control at every gamma. Recorded
because it bears on P5, which was registered before it was seen.

## Outcome (2026-09-06 22:15; 20 replicates, 0 failures; scorer `experiments/score_plasmode.py`)

**P1, P2, P3 and P4 all FAIL. P5 holds decisively. Withdrawal (a) fires.**

The regime costs structure learning nothing. At the realistic strength the aligned masks were not worse than the
closed-missingness control but slightly better, by 0.65 edges, and the difference was in the predicted direction in
only 25% of replicates. Every arm behaved the same way, and the excess over complete data sat between 1.4 and 2.5
edges regardless of alignment or regime strength. Per the registered rule the structural half of this simulation is
dropped and no claim is made from it.

**P5 holds, and it is the result.** At the realistic regime strength, every one of the twenty replicates had at least
one column falsely flagged as having value-driven missingness, with a mean of 5.15 columns of twelve; at twice the
realistic strength the mean was 10.45 of twelve. Under the closed-missingness control, which preserves every marginal
rate, every indicator-indicator dependence and every deletion sample size, the mean was 0.05 and 0.00. Within a
hospital the transplanted mask is independent of the simulated variables by construction, so every one of these
detections is a false positive, manufactured by the latent regime alone.

This inverts the paper's claim in a way worth stating plainly. The regime does not make you recover a worse graph.
It makes you diagnose the wrong mechanism: a method whose correction step is premised on detecting missingness
explained by observed values will find that signal where none exists, in proportion to the strength of the regime.

**Post hoc, flagged as such and not registered.** The aligned masks being slightly better than the control has a
plausible explanation: when the mask is aligned with the hospital, the rows surviving a test-wise deletion come
disproportionately from hospitals that record those variables, so deletion partially stratifies on the latent regime
and removes some of the confounding it induces. This was not predicted, is a small effect, and would need its own
experiment before it could be claimed.

Scorer output, verbatim:

```
=== PLASMODE (20 replicates) ===
P1 td_pc aligned-minus-control at gamma 1: mean -0.65 edges (needs >= 1.0), positive in 25% (needs >= 70%): FAILS
P2 td_pc gap by gamma: 0.0:-0.25 1.0:-0.65 2.0:-0.15 non-decreasing False, gamma 0 gap -0.25 (needs <= 0.5): FAILS
P3 mvpc gap +0.00 vs td_pc -0.65, ratio -0.00 (needs >= 0.7): FAILS
P4 cdnod_est gap ratio 1.00 (needs <= 0.5) and within 0.00 edges of cdnod_true (needs <= 1.0): FAILS
P5 share of replicates with >= 1 falsely flagged column: g0.0/alig:10% g0.0/clos:10% g1.0/alig:100% g1.0/clos:5% g2.0/alig:100% g2.0/clos:0%
   at gamma 1 aligned: 100% (needs >= 50%): HOLDS

mean skeleton distance to the true graph (target A), by arm:
arm              cdnod_est  cdnod_true  complete   fci  mvpc  td_pc
gamma alignment                                                    
0.0   aligned         4.60        4.60      3.15  4.95  5.55   4.60
      closed          4.85        4.85      3.15  4.95  5.35   4.85
1.0   aligned         4.60        4.60      3.15  4.90  5.55   4.60
      closed          5.25        5.25      3.15  5.40  5.55   5.25
2.0   aligned         5.10        5.10      3.40  5.30  5.85   5.10
      closed          5.25        5.25      3.40  5.25  5.65   5.25

mean excess over the complete-data arm:
arm              cdnod_est  cdnod_true  complete   fci  mvpc  td_pc
gamma alignment                                                    
0.0   aligned         1.45        1.45       0.0  1.80  2.40   1.45
      closed          1.70        1.70       0.0  1.80  2.20   1.70
1.0   aligned         1.45        1.45       0.0  1.75  2.40   1.45
      closed          2.10        2.10       0.0  2.25  2.40   2.10
2.0   aligned         1.70        1.70       0.0  1.90  2.45   1.70
      closed          1.85        1.85       0.0  1.85  2.25   1.85

spurious detections (mean count of falsely flagged columns):
gamma  alignment
0.0    aligned       0.10
       closed        0.10
1.0    aligned       5.15
       closed        0.05
2.0    aligned      10.45
       closed        0.00

secondary, with self-masking at gamma 1:
arm        cdnod_est  cdnod_true  complete  fci  mvpc  td_pc
alignment                                                   
aligned         1.85        1.85       0.0  2.1  2.65   1.85
closed          1.70        1.70       0.0  2.0  2.60   1.70
```
