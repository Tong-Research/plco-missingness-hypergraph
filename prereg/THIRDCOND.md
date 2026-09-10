# Pre-registration: does the tree-vs-linear gap on the modal pattern predict the tree-vs-hierarchy gap on incomplete data? (APPROVED)

Status: APPROVED by the user 2026-09-06 10:02 ("Run test on the other homelab machine"), written before any holdout row
is scored by the runner. Runner `experiments/third_condition.py`, scorer `experiments/score_thirdcond.py`.

## Why this test exists

The paragraph "A third condition" (sec:res-semisynth, added 2026-09-05) ends with a testable claim that was never tested:
*where a tree beats a linear model on complete data, it will beat a hierarchy of linear models on incomplete data.*
Before writing this registration, the complete-case counts of the 17 holdout halves were checked (structure only, no
outcome): **12 of 17 have fewer than 60 complete cases, and 9 have none at all.** The pre-training test as written is
inapplicable exactly where structured missingness is pervasive, which is the paper's whole domain. The sentence is
therefore reworded, before this test, to the **rows of the most common (modal) observed pattern**, on which both models
fit with no missingness handling because every row is complete within that pattern's own columns. This registration
tests the reworded claim.

## Design

Real data: the 17 sweep datasets, holdout halves capped at 200,000 (generator seed 0), exactly as the sweep rows used.
Semi-synthetic: cand_higgs and sweep_42739 masks on dev halves (60,000), outcome regenerated with
`semisynthetic_masks.make_y` at delta in {0, 0.25, 0.5, 1.0}, seed 42 — the same generation as `results/semisynth_*.csv`.
On the modal pattern's rows (its observed columns only): tuned logistic regression (LogisticRegressionCV, Cs=6, inner
3-fold, AUPRC) vs default HistGradientBoosting, 3-fold stratified CV, paired median AUPRC gap `gap_modal = tree - LR`.
The complete-case subset is scored the same way where it has >= 2,000 rows. A modal subset is "applicable" if it has
>= 2,000 rows and >= 50 records of each class. The incomplete-data gap `gap_inc = tree - family_cv` comes from the
existing committed files (`results/cand/*.csv`, paired median), not recomputed.

## Predictions

P1 (the falsifiable half). On the semi-synthetic cells where the CV hierarchy beats the tree on incomplete data by
   >= 0.013 (Higgs delta 0.5 and 1.0; road safety delta 0.5 and 1.0, per `results/semisynth_*.csv`), tuned LR ties or
   beats the tree on the modal pattern: `gap_modal <= +0.005` on all four cells. If the tree beats LR on the modal
   pattern AND the hierarchy still beats the tree on the incomplete data, the claim is false as stated.
P2. On every applicable real dataset, `gap_modal > 0` — the tree beats linear on the modal rows wherever it beats the
   hierarchy on the incomplete data (it beats the hierarchy on all 17).
P3. Across applicable real datasets, Spearman(gap_modal, gap_inc) >= 0.5 — the modal gap is a useful quantitative
   predictor, not just a one-way implication. Requires >= 6 applicable datasets; with fewer, P3 is reported as
   underpowered, not failed.
P4 (applicability, expected from the structure check). The complete-case subset is applicable on <= 5 of 17; the modal
   subset is applicable on >= 12 of 17. This is what justifies the reword.

## Withdrawal

(a) P1 fails on any cell -> the sentence is false as a guarantee; rewrite it as a heuristic and say where it failed.
(b) P2 fails on >= 2 datasets -> same as (a).
(c) P3 fails with >= 6 applicable -> keep the one-way statement; remove any suggestion that the gap is quantitatively
    predictive.
(d) P4 fails (modal subset applicable on < 12) -> the reworded test is also inapplicable in this domain; the sentence
    must say so and the pre-training test is dropped from the guidance.

## Reporting

If P1-P3 hold: the reworded sentence stands, one clause is added citing the correlation, and a one-line table goes to
the supplement. Otherwise the sentence is rewritten per the withdrawal that fired. No other part of the paper changes.

## Disclosure (appended 2026-09-06 10:20, minutes after the freeze)

The cand_higgs semi-synthetic cells were computed on the laptop (macOS) as the runner's pipeline smoke test, in the
same shell command that wrote and froze this file. The file's text — predictions and withdrawal conditions included —
was authored in that command before it executed and was not edited after the output was read. The smoke values:
gap_modal = -0.038, -0.036, -0.040, -0.034 at delta 0, 0.25, 0.5, 1.0 (LR ahead of the tree on the modal pattern
throughout). The registered P1 reading will nevertheless be taken from the farm (Linux) run of the same cells, so that
every gap_modal in the table shares one platform (Result 198: tree numbers diverge across macOS/Linux under range
shift; no shift is applied here, and the gaps are an order of magnitude above that effect, but the rule is kept).

## Outcome (2026-09-06 10:45; all 20 jobs run on the farm, Linux and macOS as placed; scorer `experiments/score_thirdcond.py`)

- **P1 HOLDS, 5/5.** Every semi-synthetic cell where the CV hierarchy beats the tree by >= 0.013 has tuned LR ahead of
  the tree on the modal pattern (gap_modal -0.032 to -0.040). Five cells, not four: sweep_42739 at delta 0.5 qualifies
  at -0.0131, which the registered text (written from memory of the table) did not list. The rule was applied as
  written ("cells where ... by >= 0.013"), not as enumerated.
- **P2 FAILS, 13/15 -> withdrawal (b) fires.** gap_modal > 0 on 13 of 15 applicable datasets. The two failures are
  NHANES (-0.0005) and Porto Seguro (-0.0041): a tuned linear model ties the tree on the modal rows. On both the tree
  still leads the hierarchy on the incomplete data (+0.080 and +0.001). No dataset has gap_modal > 0 and gap_inc <= 0,
  so the implication in the paper's sentence is never contradicted; what fails is its converse. The condition is
  sufficient, not necessary.
- **P3 HOLDS.** Spearman(gap_modal, gap_inc) = +0.754 (p = 0.0012) over the 15 applicable datasets.
- **P4 HOLDS.** Complete-case subset applicable on 5/17 (needs <= 5); modal subset on 15/17 (needs >= 12). The two
  inapplicable rows are MIMIC-IV regimes (modal n = 1,708) and eICU regimes (modal n = 582, 2 columns; 21,259 distinct
  patterns in 47,701 rows).

Applied: the sentence is rewritten as a heuristic per (b), naming NHANES and Porto Seguro. No clause citing the
correlation is added (Reporting requires P1-P3 all to hold). No other part of the paper changes.

Notes recorded after the freeze, before the outcome was read:
- The first job list omitted `cand_eicu_regime` (one of the 17 registered rows) and ran `mimic4` (the
  `mimic4_sites` matrix, not registered) in its place by mistake. eICU was submitted separately once noticed; mimic4 is
  reported as an extra (gap_modal -0.002, modal n = 2,261) and excluded from P2-P4. The scorer's registered-set filter
  was added at that point.
- The scorer's P3 originally propagated NaN when a dataset lacked an incomplete-data file; it now drops such pairs. With
  the registered set this affects nothing (all 15 applicable rows have both gaps).
- Two failed submissions preceded the run: the code was on no worker (homelab Finding 3 regression), then the
  re-registration was a Nomad no-op on the dead job IDs (Finding 4). Neither produced any output.

Scorer output, verbatim:

```
=== semi-synthetic (P1): cells where the hierarchy beats the tree on incomplete data by >= 0.013 ===
  cand_higgs     delta 0.00  tree-hier (incomplete) -0.0076  tree-LR (modal, n=17,775) -0.0379  
  cand_higgs     delta 0.25  tree-hier (incomplete) -0.0139  tree-LR (modal, n=17,775) -0.0359  <- P1 cell HOLDS
  cand_higgs     delta 0.50  tree-hier (incomplete) -0.0201  tree-LR (modal, n=17,775) -0.0399  <- P1 cell HOLDS
  cand_higgs     delta 1.00  tree-hier (incomplete) -0.0251  tree-LR (modal, n=17,775) -0.0340  <- P1 cell HOLDS
  sweep_42739    delta 0.00  tree-hier (incomplete) -0.0047  tree-LR (modal, n=15,976) -0.0387  
  sweep_42739    delta 0.25  tree-hier (incomplete) -0.0002  tree-LR (modal, n=15,976) -0.0321  
  sweep_42739    delta 0.50  tree-hier (incomplete) -0.0131  tree-LR (modal, n=15,976) -0.0329  <- P1 cell HOLDS
  sweep_42739    delta 1.00  tree-hier (incomplete) -0.0432  tree-LR (modal, n=15,976) -0.0330  <- P1 cell HOLDS
  P1: 5/5 cells hold (needs all)

=== real holdout (P2-P4) ===
  cand_acs_income      patterns  1,261  modal n  21,992 cols  34  cc n       0  gap_modal +0.0720  gap_inc +0.0621  
  cand_airbnb          patterns     27  modal n  50,144 cols  29  cc n  50,144  gap_modal +0.0440  gap_inc +0.0535  
  cand_eicu_regime     patterns 21,259  modal n     582 cols   2  cc n       0  gap_modal +nan  gap_inc +0.0815  (modal not applicable)
  cand_higgs           patterns      6  modal n  59,461 cols  20  cc n  54,760  gap_modal +0.0693  gap_inc +0.1393  
  cand_mimic4_regime   patterns  6,156  modal n   1,708 cols  29  cc n       0  gap_modal +nan  gap_inc +0.0764  (modal not applicable)
  cand_nhanes          patterns    428  modal n   5,037 cols  47  cc n      56  gap_modal -0.0005  gap_inc +0.0801  
  cand_porto           patterns     54  modal n  70,442 cols  55  cc n  42,016  gap_modal -0.0041  gap_inc +0.0008  
  sweep_41275          patterns     17  modal n  38,396 cols   7  cc n      50  gap_modal +0.0402  gap_inc +0.0478  
  sweep_42080          patterns     15  modal n 170,528 cols   6  cc n       0  gap_modal +0.1014  gap_inc +0.0889  
  sweep_42093          patterns  1,057  modal n  23,618 cols  20  cc n       0  gap_modal +0.0234  gap_inc +0.1136  
  sweep_42136          patterns     33  modal n  75,520 cols   7  cc n       0  gap_modal +0.0000  gap_inc +0.0013  
  sweep_42333          patterns    652  modal n   6,575 cols  23  cc n       0  gap_modal +0.0015  gap_inc +0.0136  
  sweep_42737          patterns     33  modal n  77,668 cols  31  cc n       0  gap_modal +0.0201  gap_inc +0.0124  
  sweep_42739          patterns    734  modal n  48,522 cols  61  cc n  48,522  gap_modal +0.1873  gap_inc +0.1718  
  sweep_46654          patterns      4  modal n  21,859 cols  17  cc n   6,507  gap_modal +0.0063  gap_inc +0.0221  
  sweep_46703          patterns      7  modal n  87,396 cols  17  cc n       0  gap_modal +0.0027  gap_inc +0.0027  
  sweep_46725          patterns     16  modal n  82,166 cols   7  cc n       0  gap_modal +0.1432  gap_inc +0.1030  

P4 applicability: complete-case >= 2000 on 5/17 (needs <= 5); modal >= 2000 on 15/17 (needs >= 12)
P2: gap_modal > 0 on 13/15 applicable (needs all; withdrawal (b) at >= 2 failures)
P3: Spearman(gap_modal, gap_inc) = +0.754 (p 0.0012) over 15 datasets with both gaps (needs >= 0.5)
EXTRA (not registered, excluded): mimic4 modal n 2,261 gap_modal -0.0024
```
