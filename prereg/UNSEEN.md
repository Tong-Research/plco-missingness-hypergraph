# UNSEEN: Good-Turing mass of never-seen missingness patterns (pre-registered 2026-09-06 11:20)

Idea 3 of the 2026-09-06 round. eICU regimes has 21,259 distinct patterns in 47,701 rows. The share of future rows whose
pattern was never seen in training is the share for which any pattern-conditional method, or pattern-keyed audit, has no
local fit. Good-Turing estimates it from singleton counts alone.

## Design (`experiments/probe_unseen.py`)
17 registered datasets, full dev and holdout halves (no cap). On the fitting half: N rows, S distinct patterns, n1
singletons, n2 doubletons; GT p0 = n1/N; Chao1 = S + n1^2/(2 n2); Heaps exponent = log-log slope of distinct patterns
vs rows over the last decade of a fixed random ordering (seed 0). On the other half: unseen share = fraction of rows whose
pattern is absent from the fitting half; thin share = fraction whose pattern has fitting support < 30. Both directions
(dev->holdout and holdout->dev), 34 rows.

## Predictions
P1. |GT p0 - unseen share| <= 0.02 on >= 30 of the 34 rows.
P2. Spearman(GT p0, unseen share) >= 0.9 over the 34 rows.
P3. It matters somewhere: unseen share >= 0.05 on >= 5 of 17 datasets (dev->holdout), and eICU regimes >= 0.30.
P4. Thin share (support < 30) is >= 2x the unseen share on >= 12 of 17 (dev->holdout): the audit problem is larger than
    the unseen problem.

## Withdrawal
(a) P1 fails -> Good-Turing is not usable here (pattern frequencies are not exchangeable enough); report empirical shares only.
(b) P2 fails with P1 holding -> the calibration is fine only in absolute terms; no ranking claims.
(c) P3 fails -> the statistic is a curiosity; no paper, one sentence in Paper 1's discussion at most.
(d) P4 fails -> drop the audit framing; keep the unseen framing only.

## Disclosure (appended 2026-09-06 11:40, after the freeze, before the farm run was read)
A smoke test on dugong ran the script on sweep_46654 and, after a loader bug was fixed (per-slice column drop shifted
indices; every pattern looked unseen), on cand_eicu_regime: GT p0 0.333 vs unseen share 0.330 (dev->holdout), thin
share 0.803, Heaps 0.79, Chao1 70,945. The eICU numbers were seen before the farm run; the predictions were not edited.
The registered reading is taken from the farm output of the same script.

## Outcome (2026-09-06 12:15; 17/17 datasets on the farm; scorer `experiments/score_probes.py`)

P1 HOLDS (34/34, max error 0.0025), P2 FAILS (Spearman 0.885; ties at zero on nine datasets), P3 FAILS (unseen
>= 0.05 on 2/17; eICU 0.330 holds), P4 HOLDS (17/17).
Withdrawals (b) and (c) fire: no ranking claims, and the statistic is a curiosity outside the ICU regime matrices. The
one-sentence allowance is used in Paper 1's discussion. Good-Turing itself is essentially exact here (worst error
0.0025 on 34 comparisons), and Chao1 puts eICU's total pattern count near 71,000 against 21,248 seen; the thin share
(support < 30) is 0.80 on eICU and 0.46 on MIMIC-IV regimes. Smoke disclosure above: the eICU numbers were seen before
the farm run.

Scorer output, verbatim:

```
=== UNSEEN (17/17 datasets, 34 rows) ===
P1 |GT p0 - unseen| <= 0.02 on 34/34 needs >= 30: HOLDS   (max err 0.0025)
P2 Spearman(GT p0, unseen) = +0.885 needs >= 0.9: FAILS
P3 unseen >= 0.05 on 2/17 (needs >= 5) and eICU 0.330 (needs >= 0.30): FAILS
P4 thin >= 2x unseen on 17/17 needs >= 12: HOLDS
                     N_fit  patterns_fit   gt_p0  unseen_share  thin_share   heaps       chao1
dataset                                                                                       
cand_acs_income     711281          1554  0.0004        0.0004      0.0097  0.1819   1860.4464
cand_airbnb          93349            26  0.0001        0.0001      0.0007  0.1412     38.5000
cand_eicu_regime     47496         21248  0.3326        0.3301      0.8034  0.7922  70944.6953
cand_higgs          409529             6  0.0000        0.0000      0.0000 -0.0000      6.0000
cand_mimic4_regime   33458          6147  0.1168        0.1151      0.4572  0.6645  16216.0297
cand_nhanes          14910           421  0.0135        0.0141      0.0905  0.4778    734.8769
cand_porto          298207            66  0.0000        0.0001      0.0007  0.2442     87.1250
sweep_41275          65265            15  0.0000        0.0001      0.0011  0.0846     17.0000
sweep_42080         199564            18  0.0000        0.0000      0.0002  0.1413     20.2500
sweep_42093         182453          1082  0.0014        0.0012      0.0269  0.2674   1342.0156
sweep_42136         200167            28  0.0000        0.0000      0.0005  0.1224     28.1000
sweep_42333          44876           665  0.0043        0.0036      0.0668  0.3581    914.0811
sweep_42737         199881            38  0.0000        0.0000      0.0004  0.1618     38.2857
sweep_42739         181625           746  0.0018        0.0017      0.0114  0.4265   1248.9762
sweep_46654          50110             5  0.0000        0.0000      0.0000  0.1184      5.0000
sweep_46703         200044             7  0.0000        0.0000      0.0000  0.2693      8.0000
sweep_46725         200339            23  0.0000        0.0000      0.0001  0.3301     43.2500
```
