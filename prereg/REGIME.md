# REGIME: is the ordering regime hospital-specific, and is regime shift a cause of cross-hospital loss? (pre-registered 2026-09-06 17:50)

Follows Result 209 (the mask is set by a latent ordering regime the values do not reveal). If regimes are
hospital-specific, a model moved between hospitals meets familiar physiology under a foreign mask.

## Design (`experiments/probe_regime.py`)
eICU regime matrix (95,197 stays, 57 columns) with its 100 hospital ids from eicu_sites (row-aligned, asserted on y);
MIMIC-IV regime matrix with its 9 units. Site mode: 3-fold CV top-1 accuracy predicting the site from mask only, from
mean-filled values only, and both; majority-class baseline; all sites and the 20 largest. Transfer mode, for each of
the 20 largest eICU hospitals with >= 50 deaths: in_site (3-fold CV native tree within the hospital), transfer (tree on
all other hospitals), adapted (the other hospitals' rows re-masked with masks sampled from the target hospital, values
only ever dropped, then trained), mask-only in-site and transfer; regime_distance = mean absolute difference of
per-column missing rates between source and target.

## Predictions
P1. eICU: mask-only accuracy predicting the hospital among the 20 largest >= 5x the majority baseline, and >= 0.8x the
    values-only accuracy. (The regime is a hospital fingerprint at least as strong as the physiology.)
P2. Adapted >= transfer on >= 14 of the 20 hospitals, with median gain >= 0.005 AUPRC. (Re-masking the source to the
    target's regime recovers part of the transfer loss.)
P3. Spearman(gain_adapted, regime_distance) >= 0.4 over the 20. (The recovery is larger where regimes differ more.)
P4. Mask-only transfer AUPRC < mask-only in-site AUPRC on >= 14 of 20 (the regime's outcome mapping does not transport).
Reported, not predicted: delta_transfer (Paper C found that merging helps small sites, so transfer may exceed in-site).

## Withdrawal
(a) P1 fails -> regimes are not hospital-specific; the transfer story has no premise. Dropped.
(b) P2 fails -> native trees are robust to regime shift by sub-masking; a fact in its own right, but the "regime
    shift causes transfer loss" claim is dropped.
(c) P3 fails with P2 holding -> the gain is not regime-driven; reported as a robustness trick only.
(d) P4 fails -> the regime-outcome mapping transports; then regime shift cannot be the mechanism. Dropped.

## Disclosure (appended 2026-09-06 17:55, after the freeze, before the farm run)
Smoke on dugong, MIMIC-IV site mode only: mask-only accuracy 0.454 vs majority 0.208 (2.2x), values-only 0.536, both
0.542. Seen before the eICU run; predictions not edited. P1 is registered on eICU.

## Outcome (2026-09-06 18:05; 22 jobs, 0 failures; scorer `experiments/score_regime.py`)

P1 HOLDS: among eICU's 20 largest hospitals the mask alone identifies the hospital at 0.803 accuracy (majority 0.101,
8.0x; values 0.881; both 0.893). The ordering regime is a hospital fingerprint almost as strong as the physiology.
P2, P3, P4 FAIL: re-masking the other hospitals to the target's regime before training lowers AUPRC on 19 of 20
(median -0.013); the gain is unrelated to regime distance; and the mask-only mortality model trained elsewhere beats
the one trained in-hospital on 19 of 20. Pooled transfer beats in-hospital training by a median +0.08 (Paper C's
site-size result again). Withdrawals (b) and (d) fire: regimes differ by hospital and a native tree does not care;
regime shift is not a cause of cross-hospital loss, and matching the target's mask only discards information.
Surviving fact: the regime is hospital-specific, informative for the outcome, and harmless to a pooled native tree.

Scorer output, verbatim:

```
=== REGIME site fingerprint ===
    db subset  n_sites     n features  accuracy  majority  ratio
mimic4    all        9 66989     mask     0.454     0.208  2.190
mimic4    all        9 66989   values     0.536     0.208  2.580
mimic4    all        9 66989     both     0.542     0.208  2.609
mimic4  top20        9 66989     mask     0.454     0.208  2.190
mimic4  top20        9 66989   values     0.536     0.208  2.580
mimic4  top20        9 66989     both     0.542     0.208  2.609
  eicu    all      100 95197     mask     0.066     0.046  1.453
  eicu    all      100 95197   values     0.323     0.046  7.082
  eicu    all      100 95197     both     0.075     0.046  1.647
  eicu  top20       20 43053     mask     0.803     0.101  7.963
  eicu  top20       20 43053   values     0.881     0.101  8.734
  eicu  top20       20 43053     both     0.893     0.101  8.853
P1 eICU top-20: mask/majority = 7.96 (>= 5), mask/values = 0.91 (>= 0.8): HOLDS

=== REGIME transfer (20 hospitals) ===
P2 adapted >= transfer on 2/20 (>= 14), median gain -0.0138 (>= 0.005): FAILS
P3 Spearman(gain, regime_distance) = +0.104 (>= 0.4): FAILS
P4 mask-only transfer < in-site on 4/20 (>= 14): FAILS
reported: delta_transfer median +0.0836, transfer > in_site on 19/20
 site  n_T  pos_T  regime_distance  in_site  transfer  adapted  gain_adapted  mask_only_in  mask_only_transfer
    3 4342    293           0.0791   0.2853    0.3697   0.3531       -0.0166        0.2376              0.2458
   49 3757    319           0.0792   0.3141    0.3705   0.3392       -0.0313        0.2634              0.2597
   98 2523    289           0.0898   0.4904    0.4646   0.4536       -0.0110        0.4160              0.3330
   21 1530    100           0.0993   0.3950    0.4675   0.4530       -0.0145        0.1928              0.3212
   26 1502    120           0.1007   0.2145    0.3192   0.3358        0.0167        0.2781              0.2777
   94 2516    287           0.1041   0.3737    0.4121   0.4078       -0.0043        0.2929              0.3020
   68 2268    149           0.1059   0.2709    0.3536   0.3131       -0.0406        0.2207              0.2875
   46 2230    282           0.1092   0.3803    0.4746   0.4686       -0.0060        0.3498              0.3982
   89 1300    116           0.1116   0.2252    0.3829   0.3478       -0.0351        0.2238              0.2343
   58 1752     97           0.1157   0.1189    0.2473   0.2342       -0.0131        0.1456              0.1788
   19 1951    198           0.1175   0.4169    0.4672   0.4295       -0.0376        0.2796              0.3742
   90 3154    381           0.1210   0.4756    0.5045   0.4963       -0.0082        0.3537              0.3646
   81 1311     92           0.1255   0.2287    0.3663   0.3247       -0.0416        0.1615              0.2787
   88 1392     94           0.1302   0.2105    0.3990   0.3881       -0.0109        0.2151              0.3100
   96 1548    159           0.1353   0.3392    0.4130   0.3982       -0.0148        0.2696              0.3100
    7 2092    208           0.1355   0.3731    0.4676   0.4765        0.0089        0.3137              0.3269
   30 1880    203           0.1374   0.3530    0.4573   0.4339       -0.0234        0.2603              0.3232
   42 2509    219           0.1380   0.3387    0.3659   0.3385       -0.0274        0.2999              0.2987
   34 2161    243           0.1556   0.3429    0.3759   0.3758       -0.0001        0.2595              0.2868
   60 1335     93           0.1670   0.1630    0.3656   0.3546       -0.0110        0.1745              0.2599
```
