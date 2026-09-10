# PROXY: the amputed modal block as a cheap proxy benchmark (pre-registered 2026-09-06 11:20)

Idea 5 of the 2026-09-06 round. THIRDCOND found Spearman 0.75 between the tree-vs-LR gap on the modal rows and the same
gap on the incomplete data. This asks whether the real-mask-amputed modal block ranks a whole set of strategies the way
the full incomplete data does. Shares `experiments/probe_ampute.py` with AMPUTE; no extra runs.

## Design
Applicable datasets of AMPUTE. On the block under each mechanism: median-over-folds AUPRC of the four arms mean_impute,
mean_indicator, mask_interaction, histgb_native. On the full incomplete data: the paired median AUPRC of the same four
arms from the committed `results/cand/<dataset>.csv` (permuted = 0). Kendall tau between the two rankings per dataset
and mechanism; agreement of the top arm.

## Predictions
P1. Under real masks, tau >= 0.5 on >= 9 applicable datasets.
P2. Under real masks, the top arm agrees on >= 9 applicable datasets.
P3. Real masks beat mcar as a proxy: mean tau(real) > mean tau(mcar) over applicable datasets.
P4. The block is not simply the same data: the block's median AUPRC differs from the full-data AUPRC by > 0.02 for at
    least one arm on >= 8 applicable datasets (otherwise agreement is trivial).

## Withdrawal
(a) P1 fails -> the modal block is not a proxy; the THIRDCOND correlation was specific to the tree-vs-linear question.
(b) P3 fails -> the real-mask machinery adds nothing over mcar for this purpose; if P1 held, the proxy is reported with
    mcar, not real masks.
(c) P4 fails -> agreement is trivial (the block is the dataset); no claim.

## Outcome (2026-09-06 12:15; 17/17 datasets on the farm; scorer `experiments/score_probes.py`)

P1 FAILS (tau >= 0.5 on 5/14), P2 HOLDS (top arm agrees on 11/14), P3 HOLDS (mean tau 0.33 vs 0.29), P4 FAILS
(7/14, one short). Withdrawals (a) and (c) fire: the amputed modal block does not reproduce the full-data ranking of the
four arms, and on half the datasets the block is close enough to the full data that agreement would be trivial anyway.
The top arm is the tree on 11/14 both ways, which is Table sweep's finding restated. Dropped.

Scorer output, verbatim:

```
=== PROXY (applicable 14) ===
P1 tau(real) >= 0.5 on 5/14 needs >= 9: FAILS
P2 top arm agrees on 11/14 needs >= 9: HOLDS
P3 mean tau real +0.333 vs mcar +0.286: HOLDS
P4 block differs from full data by > 0.02 for some arm on 7/14 needs >= 8: FAILS
                 tau_real  tau_mcar  top_agree  maxdiff
dataset                                                
cand_acs_income     0.000     0.000          1    0.114
cand_airbnb         0.667     0.000          1    0.030
cand_higgs          1.000     0.667          1    0.094
cand_nhanes        -1.000     0.333          0    0.313
cand_porto          0.000    -0.667          0    0.022
sweep_41275         1.000     0.667          1    0.020
sweep_42080         0.000     0.000          1    0.025
sweep_42093         0.333     1.000          1    0.009
sweep_42136         0.333     0.667          1    0.001
sweep_42333         1.000     0.000          1    0.014
sweep_42737         0.333     0.333          1    0.019
sweep_42739         0.000     0.333          1    0.103
sweep_46654         0.333     0.333          0    0.013
sweep_46703         0.667     0.333          1    0.003
```
