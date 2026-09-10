# MASKINC: does the mask start to pay when the values can no longer reveal the regime? (pre-registered 2026-09-06 18:30)

Follows Result 209 and `papers/LEAD-LATENT-REGIME-MECHANISM.md`, which names this the free falsification test of the
latent-regime account. If the mask adds nothing because the observed values already reveal the regime Z (the NIMO
condition, Y independent of M given X_obs), then withholding value columns must make the mask pay.

## Design (`experiments/probe_maskinc.py`)
17 registered datasets, holdout halves capped at 60,000, 3-fold stratified CV seed 0, HCAL tree config. For q in
{1.0, 0.75, 0.5, 0.25, 0.1}, keep a random subset of ceil(q*p) value columns (3 draws at each q < 1, seeds 0-2):
arms are the retained values alone; retained values plus ALL p indicators (gain_full); retained values plus the
retained columns' indicators (gain_kept); and all indicators alone. Per dataset and q, the median over draws.

## Predictions
P1. gain_full at q = 1.0 is <= 0.005 on all 17 (Result 209 reproduced inside this script).
P2. gain_full at q = 0.1 is >= 0.01 on >= 10 of 17.
P3. Median gain_full over datasets is non-increasing in q across {0.1, 0.25, 0.5, 0.75, 1.0} (ties allowed).
P4. On the four regime-driven datasets (eICU, MIMIC-IV, NHANES, road safety) gain_full at q = 0.1 is >= 0.02.
P5. gain_kept at q = 0.1 is smaller than gain_full at q = 0.1 on >= 12 of 17 (the withheld columns' indicators are
    what carries the regime, not the retained ones').

## Withdrawal
(a) P1 fails -> the script does not reproduce Result 209 and nothing else is interpretable; fix and re-register.
(b) P2 and P4 both fail -> the values do not reveal the regime and the mask is simply uninformative given a tree;
    the redundancy explanation in Result 209 is withdrawn and replaced by "the mask carries nothing at all",
    which contradicts the mask-only lift of 2.4-4.5x and must then be investigated as an inconsistency.
(c) P3 fails with P2 holding -> the relationship is not monotone; report the curve, claim no law.
(d) P5 fails -> the effect is not about which columns were withheld; report as a general small-p effect.

## Disclosure (appended 2026-09-06 18:40, after the freeze, before the farm run)
Smoke on dugong, sweep_46654 only (a structural set with two panels and no regime to speak of): gain_full stayed
below 0.004 at every q and gain_kept was 0.000 throughout. Seen before the farm run; predictions were not edited.

## Outcome (2026-09-06 20:35; 17/17 datasets; scorer `experiments/score_rrstruct.py`)

P1 HOLDS 17/17, P2 HOLDS 13/17, P4 HOLDS 4/4, P5 HOLDS 17/17. P3 FAILS.

**P1.** Adding the full mask to a native tree gains 0.000 AUPRC on all 17 datasets when every value column is present.
Result 209's secondary finding is reproduced inside this frozen script.

**P2 and P4.** Withhold nine columns in ten and the mask starts to pay: gain >= 0.01 on 13 of 17, and >= 0.02 on all
four regime-driven sets (eICU 0.046, MIMIC-IV 0.045, NHANES 0.159, road safety 0.030). The largest is ACS income at
0.182.

**P5 is the sharp one, 17/17.** The indicators of the RETAINED columns never help, at any q: gain_kept is 0.000
everywhere. Only the indicators of the WITHHELD columns pay. So a column's indicator acts as a coarse proxy for that
column's own value, and carries nothing once the column itself is present. This is a more specific statement than the
latent-regime account requires, and it is what the data show.

**P3 FAILS on the flat end.** The median gain is 0.0235 at q = 0.1, 0.0026 at 0.25, and rounds to 0.0000 at 0.5, 0.75
and 1.0; monotonicity fails by floating-point noise among those three ties. Withdrawal (c) applies: the curve is
reported, no law is claimed. The substantive shape is as predicted.

Scorer output, verbatim:

```
=== MASKINC (17/17 datasets) ===
P1 gain_full at q=1.0 <= 0.005 on 17/17 (needs all 17): HOLDS
P2 gain_full at q=0.1 >= 0.01 on 13/17 (needs >= 10): HOLDS
P3 median gain_full by q: 0.1:+0.0235 0.25:+0.0026 0.5:+0.0000 0.75:+0.0000 1.0:+0.0000 non-increasing: FAILS
P4 gain_full at q=0.1 >= 0.02 on 4/4 regime sets: HOLDS
P5 gain_kept < gain_full at q=0.1 on 17/17 (needs >= 12): HOLDS
q                   full_q0.1  full_q0.25  full_q0.5  full_q0.75  full_q1.0  kept_q0.1  kept_q0.5
dataset                                                                                          
cand_acs_income        0.1818      0.0399     0.0011      0.0000        0.0        0.0        0.0
cand_airbnb            0.0960      0.0047     0.0013      0.0000        0.0        0.0        0.0
cand_eicu_regime       0.0457      0.0180     0.0063      0.0005        0.0        0.0        0.0
cand_higgs             0.0235      0.0005     0.0000      0.0000        0.0        0.0        0.0
cand_mimic4_regime     0.0446      0.0122     0.0031      0.0000        0.0        0.0        0.0
cand_nhanes            0.1592      0.0711    -0.0011      0.0001        0.0        0.0        0.0
cand_porto             0.0013      0.0008    -0.0005     -0.0003        0.0        0.0        0.0
sweep_41275            0.0267      0.0204     0.0055      0.0001        0.0        0.0        0.0
sweep_42080            0.0034      0.0026     0.0013      0.0011        0.0        0.0        0.0
sweep_42093            0.0182      0.0014    -0.0000     -0.0000        0.0        0.0        0.0
sweep_42136            0.0170      0.0319     0.0000      0.0000        0.0        0.0        0.0
sweep_42333            0.0429      0.0023    -0.0000      0.0000        0.0        0.0        0.0
sweep_42737            0.0102     -0.0004    -0.0000     -0.0001        0.0        0.0        0.0
sweep_42739            0.0296      0.0077     0.0047      0.0008        0.0        0.0        0.0
sweep_46654            0.0036      0.0002    -0.0002      0.0000        0.0        0.0        0.0
sweep_46703            0.0078     -0.0001     0.0000      0.0000        0.0        0.0        0.0
sweep_46725            0.0182      0.0015    -0.0000      0.0014        0.0        0.0        0.0
```
