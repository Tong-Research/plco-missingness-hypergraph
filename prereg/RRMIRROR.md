# RRMIRROR: the corrected double dissociation, confirmed on the mirror split (pre-registered 2026-09-06 20:35)

## Why this exists: a correction to Result 209
Result 209 said "each missing indicator is predicted from the rest of the record's MASK at AUROC 0.81-1.00 on every
dataset". The statistic behind it (`probe_explore2.py`, recov_outpanel) fed the model the MEAN-IMPUTED VALUES of the
out-of-panel columns, not their indicators. Mean-filling encodes missingness, so the mask was available, but so were
the values of every other column including the always-observed ones. The prose overstated what was measured. The
script's own docstring said "mean-filled"; the error is in the claim, not the code.

RRSTRUCT (frozen 18:30, fitted on dev and evaluated on holdout) supplies the clean measurement, using ONLY the other
panels' binary presences. It changes the picture and sharpens it into a double dissociation:

| set | values -> indicator | out-of-panel PRESENCES -> indicator |
|---|---|---|
| eICU regimes | 0.523 | 0.927 |
| NHANES | 0.693 | 0.887 |
| road safety (42739) | 0.713 | 0.872 |
| ACS income | 0.991 | 0.854 |
| Airbnb | 0.861 | 0.678 |
| ATLAS Higgs | 0.998 | 0.753 |
| sweep_42737 | 1.000 | 0.883 |
| sweep_46654 | 0.821 | 0.507 |
| sweep_46703 | 0.817 | 0.508 |

So the corrected fact is not "the mask predicts the mask everywhere". It is that the two regimes are opposite: where
missingness is structural the VALUES predict it and the other panels do not; where it is protocol-driven the other
panels predict it and the values do not.

**These thresholds are set AFTER seeing the numbers above.** They are therefore not confirmed by them. The
confirmation is the MIRROR split: the same frozen script with `--mirror`, fitting on the holdout half and evaluating
on the development half, which no model in this line has been fitted on in this direction.

## Predictions on the mirror split
D1. On eICU, MIMIC-IV, NHANES and road safety: mean AUROC(values) - mean AUROC(panels_tree) <= -0.15 on all four.
D2. On ACS income, Airbnb, ATLAS Higgs, sweep_42737, sweep_46654, sweep_46703: the same difference is >= +0.10 on all six.
D3. The sign of that difference agrees with the dev-fit run on all 17 datasets.
D4. P1 of RRSTRUCT reproduces: the best mixture with K <= 20 reaches >= 0.95 x the tree AUROC on >= 12 of 17.
Reported, not predicted: the seven remaining datasets, which the double dissociation does not classify.

## Withdrawal
(a) D1 or D2 fails on more than one dataset in its group -> the double dissociation is not stable; report the mirror
    numbers beside the dev-fit numbers and make no claim.
(b) D3 fails on more than two datasets -> the sign itself is unstable; the corrected fact is withdrawn entirely and
    Result 209 stands corrected with no replacement.

## Outcome (2026-09-06 20:40; 17/17 datasets, fit on holdout, evaluated on dev; scorer `experiments/score_rrmirror.py`)

**All four predictions hold.** D1 4/4 (eICU -0.405, MIMIC-IV -0.371, NHANES -0.213, road safety -0.159 against a
registered -0.15), D2 6/6 (+0.118 to +0.309), D3 17/17 (the sign agrees with the dev-fit run on every dataset, and
the magnitudes agree to within 0.02 on 16 of 17), D4 17/17.

The corrected fact stands, confirmed out of sample:

> Real tabular missingness comes in two kinds that need opposite descriptions. Where it is structural, the observed
> values determine which fields are missing (AUROC 0.82-1.00) and the other panels' presences do not (0.51-0.88).
> Where it is protocol-driven, the other panels' presences determine it (0.87-0.94) and the values do not (0.52-0.71).
> The sign of that difference is stable across a full split reversal on all seventeen datasets.

Seven datasets are not classified by the dissociation and are reported as such: two sit near zero (42333 -0.008,
42093 +0.001) and five are value-determined without being in the structural group (Porto, 46725, 42136, 41275, 42080,
+0.20 to +0.37).

Scorer output, verbatim:

```
=== RRMIRROR (17/17 datasets, fit on holdout, evaluated on dev) ===
D1 regime sets, values - panels <= -0.15 on 4/4: HOLDS   regime:-0.405 regime:-0.371 nhanes:-0.213 42739:-0.159
D2 structural sets, values - panels >= +0.10 on 6/6: HOLDS   income:+0.152 airbnb:+0.185 higgs:+0.248 42737:+0.118 46654:+0.309 46703:+0.308
D3 sign of (values - panels) agrees with the dev-fit run on 17/17: HOLDS
D4 best mixture K<=20 >= 0.95 x tree on 17/17 (needs >= 12): HOLDS
                    values  panels_tree   diff  diff_devfit       group
dataset                                                                
sweep_42333          0.947        0.955 -0.008       -0.006       other
sweep_42093          0.824        0.823  0.001        0.002       other
cand_porto           0.929        0.730  0.199        0.199       other
sweep_46725          0.863        0.639  0.223        0.223       other
sweep_42136          0.868        0.634  0.234        0.233       other
sweep_41275          0.909        0.576  0.333        0.335       other
sweep_42080          0.885        0.514  0.371        0.374       other
cand_eicu_regime     0.523        0.928 -0.405       -0.404      regime
cand_mimic4_regime   0.564        0.936 -0.371       -0.371      regime
cand_nhanes          0.681        0.895 -0.213       -0.193      regime
sweep_42739          0.714        0.874 -0.159       -0.159      regime
sweep_42737          1.000        0.882  0.118        0.117  structural
cand_acs_income      0.982        0.830  0.152        0.138  structural
cand_airbnb          0.865        0.680  0.185        0.183  structural
cand_higgs           0.998        0.750  0.248        0.246  structural
sweep_46703          0.818        0.510  0.308        0.309  structural
sweep_46654          0.818        0.509  0.309        0.313  structural
```
