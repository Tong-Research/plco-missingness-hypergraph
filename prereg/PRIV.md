# PRIV: is the missingness pattern a fingerprint beyond support size? (pre-registered 2026-09-06 15:05)

Kill test from `papers/MASK-PRIVACY-PRIOR-ART.md` §4. Known before this run (UNSEEN): the singleton-pattern share on a
47k-row half is 0.333 on eICU regimes and 0.117 on MIMIC-IV regimes; a hypothesis is that this is length of stay (support
size) in disguise.

## Design (`experiments/probe_priv.py`)
17 registered datasets, full matrix (both halves). Unicity = share of rows whose key matches no other row, averaged over
40 random column subsets per K in {2, 4, 8, 16} (seed 0). Keys: mask (statuses of the K columns); support (observed
count only); support+mask; values_status (decile bins, missing coded -1); values_only (decile bins among rows observing
all K columns). Plus the full-pattern singleton share, and mask K=8 unicity on subsamples of 5k, 10k, 20k and all rows.

## Predictions
P1. Full-pattern singleton share >= 0.25 on eICU regimes and >= 0.08 on MIMIC-IV regimes (full matrices).
P2. Support is not the fingerprint (eICU): support-only unicity < 0.01, and support+mask minus support at K=8 >= 0.15.
P3. The mask alone carries a substantial share of the value fingerprint: on both ICU regime sets, mask unicity at K=8
    >= 0.5 x values_status unicity at K=8.
P4. Not a small-population artefact: on eICU, mask K=8 unicity on all rows >= 0.5 x its value on the 5k subsample.
P5. Scope: outside the two ICU regime sets, full-pattern singleton share < 0.01 on >= 12 of 15.

## Withdrawal
(a) P1 or P2 fails -> the fingerprint is support size or absent; dropped.
(b) P3 fails -> the mask alone is too weak; only a "values plus mask" claim survives, which is not a paper.
(c) P4 fails -> the 33% is a population artefact (Achara & Acs Fig. 6 decay); dropped.
(d) P5 fails -> not a kill; the claim broadens beyond ICU and P1-P4 are re-checked on the datasets where it fails.

## Outcome (2026-09-06 15:25; scorer `experiments/score_round6.py`)

P1 HOLDS (singleton share 0.264 eICU, 0.087 MIMIC-IV on the full matrices), P5 HOLDS (15/15 non-ICU below 0.01).
P2 FAILS: support-only unicity is 0 (support size is not the fingerprint), but eight mask statuses add only 0.004.
P3 FAILS: mask K=8 unicity is 0.000 on both ICU sets against 0.50 and 0.62 for binned values with status.
P4 FAILS: mask K=8 unicity decays 0.004 -> 0.000 from 5k to 95k rows.
Withdrawals (a), (b), (c) fire. Reading: the full 57-column pattern is a fingerprint on ICU regime data (a quarter of
eICU records are alone in theirs), but no small subset of statuses is, and eight decile-binned values already identify
99.9% of records. The mask is a weak quasi-identifier next to the values it accompanies; the only surviving scenario is
a release that publishes the entire pattern while perturbing values, which is the synthetic-EHR case and would need a
membership-inference experiment on a mask-faithful generator, not a unicity argument. Dropped as registered.
Disclosure: smoke on sweep_46654 (four patterns) on dugong after the freeze; not informative.

Scorer output, verbatim:

```
=== PRIV (17/17 datasets) ===
P1 singleton share eICU 0.264 (>= 0.25), MIMIC 0.087 (>= 0.08): HOLDS
P2 eICU support-only 0.0000 (< 0.01); support+mask - support at K=8 = 0.004 (>= 0.15): FAILS
P3 mask K=8 vs values_status K=8: eICU 0.000/0.501, MIMIC 0.000/0.623 (mask >= 0.5 x values): FAILS
P4 eICU mask K=8 decay: 5000:0.004 10000:0.002 20000:0.001 95197:0.000 (all >= 0.5 x 5k): FAILS
P5 singleton share < 0.01 on 15/15 non-ICU (needs >= 12): HOLDS
key                 mask  support_mask  values_only  values_status  full_pattern  support
dataset                                                                                  
cand_acs_income      0.0         0.000        0.143          0.002         0.000      0.0
cand_airbnb          0.0         0.000        0.392          0.319         0.000      0.0
cand_eicu_regime     0.0         0.004        0.999          0.501         0.264      0.0
cand_higgs           0.0         0.000        0.864          0.401         0.000      0.0
cand_mimic4_regime   0.0         0.003        0.998          0.623         0.087      0.0
cand_nhanes          0.0         0.002        0.996          0.934         0.010      0.0
cand_porto           0.0         0.000        0.038          0.034         0.000      0.0
sweep_41275          0.0         0.000        0.585          0.148         0.000      0.0
sweep_42080          0.0         0.000          NaN          0.002         0.000      0.0
sweep_42093          0.0         0.000        0.569          0.006         0.001      0.0
sweep_42136          0.0         0.000        0.875          0.033         0.000      0.0
sweep_42333          0.0         0.000        0.917          0.237         0.002      0.0
sweep_42737          0.0         0.000        0.001          0.001         0.000      0.0
sweep_42739          0.0         0.000        0.028          0.023         0.001      0.0
sweep_46654          0.0         0.000        0.008          0.002         0.000      0.0
sweep_46703          0.0         0.000        0.128          0.001         0.000      0.0
sweep_46725          0.0         0.000        1.000          0.017         0.000      0.0
```
