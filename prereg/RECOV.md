# RECOV: is indicator benefit bounded by mask recoverability? (pre-registered 2026-09-06 11:20)

Idea 1 of the 2026-09-06 round. Results 141/142 found the mask carries nothing the values cannot supply, for outcome
prediction. This tests the column-level mechanism: an indicator can only help where the values do not already reveal it.

## Design (`experiments/probe_recov.py`)
17 registered sweep datasets (10 sweep_* + 7 cand_*), holdout halves capped at 30,000 rows (generator seed 0). The tree
(HCAL config) is fed mean-filled values so it cannot see missingness except through the indicator under test. Per column
j with missing rate in [0.01, 0.99], 3-fold stratified CV seed 0, paired folds:
- B_j = AUPRC(values + M_j) - AUPRC(values), the marginal benefit of that one indicator;
- R_val_j = AUROC of a tree predicting M_j from the mean-filled other columns;
- R_mask_j = AUROC of a tree predicting M_j from the other indicators (co-occurrence only);
- dataset level: B_all = AUPRC(values + all indicators) - AUPRC(values).
Caveat registered now: R_val includes co-occurrence that leaks through other columns' fill values; R_mask is reported
so that the two can be separated post hoc, but the predictions below are on R_val as defined.

## Predictions
P1. Pooled over all columns of all datasets, Spearman(B_j, R_val_j) <= -0.3 (benefit falls as recoverability rises).
P2. Envelope: among columns with R_val >= 0.95, the 90th percentile of B_j is <= 0.005 AUPRC.
P3. Dataset level: Spearman(B_all, 1 - mean_j R_val_j) >= 0.4 over the 17 datasets.
P4. The effect is not trivially small: at least 5% of columns have B_j >= 0.01.

## Withdrawal
(a) P1 fails -> there is no law; the idea is reported as a null and dropped.
(b) P2 fails -> the bound is false; recoverable indicators can still help (interaction with the values); dropped as a bound,
    kept only as a correlation if P1 held.
(c) P3 fails with P1 holding -> column-level only; no dataset-level diagnostic is claimed.
(d) P4 fails -> indicators barely help anywhere under this tree, so the bound is vacuous; dropped.

## Disclosure (appended 2026-09-06 11:40)
A smoke test on dugong ran the script on sweep_46654 only (a 4-pattern dataset with no small patterns), to check it runs; its numbers are not used. Predictions were not edited after it.

## Outcome (2026-09-06 12:15; 17/17 datasets on the farm; scorer `experiments/score_probes.py`)

P1 FAILS (Spearman +0.05), P2 HOLDS, P3 FAILS (-0.23), P4 FAILS (0.6% of columns with B >= 0.01).
Withdrawals (a) and (d) fire: there is no law, and the bound is vacuous. Reading: the median R_val is 1.000 and the
median R_mask 0.999. Nearly every indicator is recoverable from the other columns (largely through co-occurrence
leaking via fill values, the caveat registered above), and no indicator helps the mean-filled tree by more than
0.02 anywhere (the largest B_all is 0.020, sweep_42739). Consistent with Results 141/142, but the design has no
gradient in R to correlate against, so it is uninformative about the bound rather than a refutation of it. Dropped.

Scorer output, verbatim:

```
=== RECOV (17/17 datasets, 354 columns) ===
P1 pooled Spearman(B, R_val) = +0.050 (p 0.35, n 354) needs <= -0.3: FAILS
P2 90th pct of B where R_val >= 0.95 = +0.0017 (n 307) needs <= 0.005: HOLDS
P3 dataset-level Spearman(B_all, 1 - mean R_val) = -0.230 (n 17) needs >= 0.4: FAILS
P4 share of columns with B >= 0.01 = 0.006 needs >= 0.05: FAILS
(post hoc, not a criterion) Spearman(B, R_mask) = +0.067; median R_val 1.000, median R_mask 0.999
                     B_all      R
dataset                          
cand_acs_income    -0.0002  0.998
cand_airbnb        -0.0000  0.960
cand_eicu_regime    0.0014  0.960
cand_higgs          0.0007  0.999
cand_mimic4_regime  0.0015  0.980
cand_nhanes         0.0087  0.990
cand_porto          0.0004  0.983
sweep_41275         0.0018  0.911
sweep_42080        -0.0013  0.848
sweep_42093         0.0000  0.897
sweep_42136         0.0001  0.862
sweep_42333         0.0004  0.988
sweep_42737         0.0000  1.000
sweep_42739         0.0199  0.996
sweep_46654         0.0001  0.985
sweep_46703         0.0000  0.985
sweep_46725         0.0002  0.864
```
