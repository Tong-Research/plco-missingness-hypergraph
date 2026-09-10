# AMPUTE: real-mask amputation of the modal block vs the MCAR benchmark (pre-registered 2026-09-06 11:20)

Idea 4 of the 2026-09-06 round. Twelve of seventeen real datasets have < 60 complete rows, so the standard imputation
benchmark (ampute complete data under a simulated mechanism) cannot run on them. The modal pattern's block is complete
within its own columns; amputing it with masks drawn from the same dataset gives real structure with ground truth.

## Design (`experiments/probe_ampute.py`)
17 registered datasets, holdout halves capped at 200,000. Modal block = rows of the most frequent observed pattern, its
own columns, capped at 20,000 rows (seed 0); applicable if >= 2,000 rows and >= 50 of each class. Mechanisms: real (each
row receives the projection onto the block's columns of a random holdout row's mask), mcar (iid cells at the real overall
rate), colmatched (independent columns at the real per-column rates: same marginals, no co-occurrence). 3-fold
stratified CV seed 0. Imputation RMSE on removed test cells, standardised by the true train sd, for mean / iterative
(5 sweeps) / kNN(5) fitted on the amputed train fold. Downstream AUPRC for mean_impute, mean_indicator,
mask_interaction (tuned LR, as in results/cand) and histgb_native, plus an oracle tree on the un-amputed block.
Per dataset and mechanism: median over folds.

## Predictions
P1. The iterative imputer's advantage over mean (RMSE_mean - RMSE_iter) is smaller under real masks than under mcar by
    >= 0.02 standardised units on >= 8 applicable datasets (co-missing columns leave the imputer fewer predictors).
P2. The tree's downstream lead over the best linear arm is larger under real than under mcar on >= 8 applicable datasets.
P3. The RMSE ranking of the three imputers differs between mcar and real on >= 4 applicable datasets.
P4. colmatched sits between: |advantage_real - advantage_colmatched| < |advantage_real - advantage_mcar| on >= 8
    applicable (marginals explain part of the gap, co-occurrence the rest).
Applicability expected on >= 12 of 17 (THIRDCOND found 15).

## Withdrawal
(a) P1 and P3 both fail -> MCAR on the modal block is an adequate stand-in for imputation quality; the critique is empty
    for imputers; dropped for that purpose.
(b) P2 fails -> and for downstream models; the whole critique is dropped.
(c) P4 fails -> co-occurrence is not the operative structure; the mechanism story is withdrawn even if P1 held.

## Disclosure (appended 2026-09-06 11:40)
A smoke test on dugong ran the script on sweep_46654 only (a 4-pattern dataset with no small patterns), to check it runs; its numbers are not used. Predictions were not edited after it.

## Outcome (2026-09-06 12:15; 17/17 datasets on the farm; scorer `experiments/score_probes.py`)

P1 FAILS (7/14, one short), P2 FAILS (5/14), P3 HOLDS (7/14), P4 HOLDS (13/14).
Applicability: 16/17 had a usable block; sweep_46725's block columns are never missing anywhere (real rate 0), so 14
count. Withdrawal (b) fires as written: downstream, MCAR on the modal block is as good a stand-in as real masks, so the
critique is dropped. The imputation-quality half is mixed: MCAR misorders the three imputers on half the datasets, and
column-matched independent masks reproduce the real-mask result on 13/14, so what matters is per-column rates, not
co-occurrence. The iterative imputer diverged on Airbnb under column-matched masks (RMSE 8.7 vs 1.0 for mean); kept as data.

Scorer output, verbatim:

```
=== AMPUTE (17/17 datasets, applicable 16) ===
P1 iterative advantage smaller under real than mcar by >= 0.02 on 7/14 needs >= 8: FAILS
P2 tree lead larger under real than mcar on 5/14 needs >= 8: FAILS
P3 imputer RMSE ranking differs mcar vs real on 7/14 needs >= 4: HOLDS
P4 colmatched closer to real than mcar is on 13/14 needs >= 8: HOLDS
mech             adv_colmatched  adv_mcar  adv_real  lead_colmatched  lead_mcar  lead_real
dataset                                                                                   
cand_acs_income           0.000     0.136     0.020            0.057      0.058      0.050
cand_airbnb              -7.682     0.291     0.099            0.035      0.032      0.033
cand_higgs                0.771     0.398     0.674            0.058      0.076      0.064
cand_nhanes               0.321     0.324     0.101           -0.032      0.003     -0.036
cand_porto                0.331     0.111     0.345           -0.003     -0.002     -0.002
sweep_41275               0.056     0.039     0.064            0.028      0.022      0.027
sweep_42080               0.000    -0.089     0.000            0.055      0.055      0.057
sweep_42093               0.191     0.290     0.045            0.000      0.002      0.000
sweep_42136               0.059     0.217     0.055            0.000      0.000      0.000
sweep_42333               0.292     0.399     0.293            0.010      0.010      0.008
sweep_42737               0.775     0.635     0.717            0.014      0.014      0.013
sweep_42739               0.182     0.203     0.065            0.103      0.095      0.107
sweep_46654               0.948     0.163     0.960            0.000      0.012     -0.000
sweep_46703               0.757     0.168     0.754            0.001      0.004      0.001
```
