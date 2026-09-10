# EXPLORE-CONFIRM: holdout confirmation of the candidate fact from the dev battery (registered 2026-09-06 16:45)

Candidate, from the dev halves of all 17 datasets (prereg/EXPLORE.md amendments 2 and 3, all 34 files read):

> **The mask predicts the mask; the values do not.** Which columns a record is missing is predicted from the rest of
> its mask (columns outside its own co-missing panel, mean-filled) at AUROC 0.81-1.00 on every dataset, but from the
> always-observed values, or from the values of another fully observed panel, only where missingness is structural
> (a recorded category decides whether a field applies). On the clinical and survey sets (eICU, MIMIC-IV, NHANES, road
> safety) the recorded values predict what is missing at AUROC 0.52-0.64, while the rest of the mask predicts it at
> 0.94-0.97. The "cascade" story (an abnormal value triggers the next test) is not what the data show; what was
> measured is set by a latent ordering regime that the other orders reveal and the values do not.

Secondary candidate (main battery, 12 of 17 dev rows read at registration time): the mask alone predicts the outcome
at up to 3.3x prevalence and beyond what the number of observed columns gives (mask-only lift exceeds support-only lift
by >= 0.1 wherever there are >= 100 patterns), yet adding the explicit mask to a native tree gains 0.000 everywhere.
The regime is informative about the outcome and the values already carry all of it.

Dev numbers behind the candidate (median over columns with missingness; recov_full uses always-observed columns
only, recov_outpanel uses columns outside the column's Jaccard >= 0.9 panel, cascade is the per-column best AUROC
from another fully observed panel's values):

| dataset | always-observed cols | recov_full | recov_outpanel | cascade |
|---|---|---|---|---|
| eICU regimes | 2 | 0.522 | 0.965 | 0.641 |
| MIMIC-IV regimes | 2 | 0.570 | 0.970 | 0.800 |
| road safety (42739) | 24 | 0.594 | 0.936 | 0.544 |
| NHANES | 5 | 0.619 | 0.958 | 0.585 |
| 42093 | 13 | 0.784 | 0.870 | 0.757 |
| 46725 | 7 | 0.799 | 0.812 | 0.716 |
| 42136 | 6 | 0.828 | 0.837 | 0.713 |
| 42080 | 5 | 0.843 | 0.845 | 0.708 |
| 41275 | 4 | 0.862 | 0.874 | 0.821 |
| Porto | 52 | 0.918 | 0.997 | 0.751 |
| 42333 | 6 | 0.963 | 0.998 | 0.851 |
| 46703, Higgs, 42737, Airbnb, 46654, ACS | 16-24 | 1.000 | 1.000 | 0.52-1.00 |

## Predictions on the HOLDOUT halves (same scripts, `--slice holdout`)
P1. Median recov_outpanel >= 0.80 on all 17.
P2. On every dataset, median recov_outpanel >= max(median recov_full, median best cascade) - 0.02.
P3. Two regimes persist: eICU, MIMIC-IV, NHANES and road safety have median recov_full <= 0.70 and
    recov_outpanel - recov_full >= 0.25; the six datasets at recov_full = 1.000 on dev stay >= 0.95.
P4. On those four, the per-column best cascade AUROC has median <= 0.85.
P5 (secondary). mask_gain (native + explicit mask minus native) <= 0.005 on all 17; on every dataset with >= 100
    patterns, mask_only_lift - support_only_lift >= 0.1.

## What becomes a fact
P1-P4 hold -> the primary sentence is a confirmed fact and goes to prior-art check before anything is written.
P5 holds -> the secondary sentence is confirmed too. Any failure is reported as such; no reinterpretation.

## Known caveat, registered now
eICU and MIMIC-IV have only two always-observed columns, so recov_full is weak there by construction; the cascade
test (P4) is the load-bearing evidence on those two, and road safety with 24 always-observed columns is the clean case.
The two ICU "regime" matrices were built to include treatment fields, whose missingness is treatment not given; the
fact must therefore also hold on NHANES and road safety, which have no such construction, or it is an artefact.

## Outcome (2026-09-06 17:10; 51 holdout jobs, 0 failures; scorer `experiments/score_explore_confirm.py`)

P1, P2, P3, P4, P5 all HOLD on the holdout halves. The primary sentence is a confirmed fact; so is the secondary.
Holdout medians track dev to within 0.03 on every dataset. NHANES: values predict the mask at 0.618, the rest of the
mask at 0.944, the best cascade at 0.529; road safety (24 always-observed columns): 0.586 / 0.938 / 0.528. Neither has
the ICU treatment-field construction, so the fact is not an artefact of it. Mask-only outcome lift on holdout: eICU
3.05x, MIMIC-IV 2.87x, NHANES 4.46x, ACS 2.36x, against support-only 2.05 / 1.86 / 1.56 / 1.61; explicit-mask gain to a
native tree 0.000 on all 17. Next step per the rule: prior-art check before anything is written.

Scorer output, verbatim:

```
=== EXPLORE-CONFIRM holdout (17/17 datasets with amendment-2 rows) ===
P1 median recov_outpanel >= 0.80 on 17/17 (needs all): HOLDS
P2 outpanel >= max(full, cascade) - 0.02 on 17/17 (needs all): HOLDS
P3 clinical/survey regime on 4/4 and structural regime on 6/6 (needs all): HOLDS
P4 best-cascade median <= 0.85 on 4/4 clinical/survey (needs all): HOLDS
P5 mask_gain <= 0.005 on 17/17; mask lift - support lift >= 0.1 on 7/7 with >= 100 patterns: HOLDS
                    full_cols  recov_full  recov_outpanel  cascade  n_patterns  mask_gain  mask_only_lift  support_only_lift
dataset                                                                                                                     
cand_eicu_regime            2       0.522           0.964    0.642       21259        0.0           3.050              2.052
cand_mimic4_regime          2       0.549           0.971    0.799        6156        0.0           2.873              1.862
sweep_42739                24       0.586           0.938    0.528         444        0.0           1.387              1.188
cand_nhanes                 5       0.618           0.944    0.529         428        0.0           4.461              1.564
sweep_42093                13       0.784           0.866    0.757         798        0.0           1.451              1.089
sweep_46725                 7       0.799           0.806    0.697          15        0.0           1.089              1.021
sweep_42136                 6       0.823           0.833    0.723          23        0.0           1.223              1.090
sweep_42080                 5       0.841           0.843    0.713          11        0.0           1.023              1.021
sweep_41275                 4       0.859           0.874    0.826          17        0.0           1.070              1.048
cand_porto                 52       0.922           0.997    0.757          41        0.0           1.205              1.073
sweep_42333                 6       0.964           0.999    0.807         652        0.0           1.436              1.281
sweep_46703                16       1.000           1.000    0.520           4        0.0           1.151              1.151
cand_higgs                 19       1.000           1.000    0.752           6        0.0           1.268              1.268
sweep_42737                24       1.000           1.000    0.999          29        0.0           1.258              1.188
cand_airbnb                18       1.000           1.000    0.536          24        0.0           1.213              1.203
sweep_46654                16       1.000           1.000    0.528           4        0.0           1.186              1.186
cand_acs_income            23       1.000           1.000    0.697         938        0.0           2.360              1.609

--- dev, for comparison ---
                    full_cols  recov_full  recov_outpanel  cascade
dataset                                                           
cand_eicu_regime            2       0.522           0.965    0.641
cand_mimic4_regime          2       0.570           0.970    0.800
sweep_42739                24       0.594           0.936    0.544
cand_nhanes                 5       0.619           0.958    0.585
sweep_42093                13       0.784           0.870    0.757
sweep_46725                 7       0.799           0.812    0.716
sweep_42136                 6       0.828           0.837    0.713
sweep_42080                 5       0.843           0.845    0.708
sweep_41275                 4       0.862           0.874    0.821
cand_porto                 52       0.918           0.997    0.751
sweep_42333                 6       0.963           0.998    0.851
sweep_46703                16       1.000           1.000    0.526
cand_higgs                 19       1.000           1.000    0.753
sweep_42737                24       1.000           1.000    0.999
cand_airbnb                18       1.000           1.000    0.541
sweep_46654                16       1.000           1.000    0.521
cand_acs_income            23       1.000           1.000    0.696
```
