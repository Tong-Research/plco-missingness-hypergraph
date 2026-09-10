# LOWQ — does the containment hierarchy pay where the values are scarce?

**Written 2026-09-08 13:20, BEFORE any measurement.** No arm of this design has been run at
q < 1. Predictions, decision rules and withdrawal conditions are fixed here.

## Why this question, and why now

Every evaluation of Paper 1's estimator has been run at full or near-full schema:
`FEATURE_SETS = ("baseline", "full")` is d=91 and d=114 on prostate — "full" adds columns. Paper
3's bound is measured in the same regime.

MASKINC measured what the mask is worth to a native tree as value columns are withheld
(`results/maskinc/`, 17 datasets, recomputed today):

| values retained | median mask gain | datasets > 0.002 |
|---|---|---|
| 100% | **+0.00000** | **0 / 17** |
| 50% | +0.00000 | 4 / 17 |
| 10% | **+0.02349** (max +0.18) | **16 / 17** |

So the entire method literature of this project sits in the one regime where the mask is
measured to be worth exactly nothing, and the regime where it is worth something has never been
tested with the method. That regime is also the federated cross-dataset setting: a target site
holding a partial schema *is* a reduced-feature site.

## The mechanism, and why the prediction is stratified

Result 209 splits the corpus in two. Where missingness is **structural**, the values predict the
mask (AUROC to 1.00), so the pattern is close to a deterministic function of the values and a
pattern-conditional model has nothing the values do not already carry. Where it is
**protocol-driven**, the values predict the mask at 0.52-0.62 while the other panels predict it at
0.87-0.93 — the pattern carries institutional information the values lack.

If the hierarchy ever pays, it must pay in the protocol-driven group and at low q. That is the
prediction, and it is derived from a measured fact rather than from the formalism.

## The counter-prior, stated before running

Two committed results predict this fails:

- **Result 212**: a column's indicator is a proxy for that column's own value and nothing else.
- **AMPUTE (Result 204)**: column-matched independent masks reproduce real masks on 13/14
  datasets, so co-occurrence structure is not what makes missingness bite.

Both say the low-q gain is *per column*, which plain indicators capture, and that the containment
structure adds nothing on top. This is the null below and it is the likelier outcome.

## Design

`experiments/probe_lowq.py`. Holdout slice, cap 20,000 rows, 3-fold stratified CV (seed 0), the
17 MASKINC datasets. For q in {1.0, 0.5, 0.25, 0.1} keep a random subset of ceil(q*p) value
columns — one draw at q=1.0, two draws (seeds 0,1) otherwise.

Four arms, on the retained columns only:

| arm | what it is |
|---|---|
| `mean_impute` | tuned logistic on mean-imputed retained values (`run_candidate.tuned`) |
| `mean_indicator` | the same plus the retained columns' indicators — **the matched comparator** |
| `family_cv` | the CV-selected hierarchy, rule x kappa on an inner 3-fold (`run_candidate.family_cv`) |
| `histgb_native` | native gradient-boosted tree, for context |

`mean_indicator` is the comparator because it sees **exactly the same information** as the
hierarchy — the retained values and their missingness — and differs only in how it uses it. The
hierarchy partitions on the pattern; the flat model gets the pattern as features. A comparison
against `mean_impute` alone would credit the hierarchy for information rather than for structure,
and is reported only as context.

Primary quantity: `family_cv - mean_indicator`, paired within (dataset, q, draw, fold).

## Stratification, fixed here

From Result 209, unchanged:

- **protocol-driven (4):** cand_eicu_regime, cand_mimic4_regime, cand_nhanes, sweep_42739
- **structural (6):** cand_acs_income, cand_airbnb, cand_higgs, sweep_42737, sweep_46654, sweep_46703
- **unclassified (7):** cand_porto, sweep_41275, sweep_42080, sweep_42093, sweep_42136, sweep_42333, sweep_46725

Two source collisions are recorded so no analysis treats them as independent: sweep_46654 and
sweep_46703 are both jigsaw; sweep_42136 and sweep_46725 are both Los Angeles crime data.

## Predictions

- **P1.** At q = 0.1, `family_cv - mean_indicator` has a paired median >= +0.002 with p < 0.05 on
  at least 3 of the 4 protocol-driven datasets.
- **P2.** The gain is larger at q = 0.1 than at q = 1.0 in the protocol-driven group (paired,
  per dataset, on at least 3 of 4).
- **P3.** In the structural group the gain is < +0.002 at every q on at least 5 of 6 — the
  hierarchy does not pay where the values determine the mask.
- **P4 (the counter-prior's null).** Across all 17 at every q, `family_cv - mean_indicator` is
  below +0.002 on at least 14.

P1 and P4 cannot both hold. P4 is the outcome Results 212 and 204 predict.

## Withdrawal and reporting

- If **P1 fails**, the hierarchy does not pay even in the regime where the mask demonstrably
  carries signal and where the structure was most likely to matter. That closes the estimator
  question in every regime, and Papers 1 and 3 gain a sentence saying so: the bound is not an
  artefact of the full-schema setting. **This is a reportable result, not a discarded run.**
- If **P1 holds and P3 holds**, the finding is that the containment structure pays where
  missingness is protocol-driven and the schema is thin — which is the cross-dataset federation
  setting — and it is reported with the stratification, not as a general win.
- If **P1 holds and P3 fails**, the gain is not mechanism-specific and the Result 209 account
  does not explain it. Report as unexplained and do not claim the mechanism.
- Any dataset that fails to run is reported by name; none is dropped silently.
- Every number quoted comes from the committed `results/lowq/*.csv`.

No arm, threshold, q value or dataset is added after the first number exists.

## Pre-measurement notes, appended 2026-09-08 13:30 (before any registered number exists)

1. **Smoke test.** `probe_lowq.py` was run once on `sweep_41275` at `--max-n 2000`, an order of
   magnitude below the registered cap of 20,000, purely to verify the code path executes. Its
   numbers are not a registered measurement and are not used anywhere.

2. **One design flaw it exposed, fixed before dispatch.** On a narrow schema several q values
   round to the same retained-column count: at p=8, q=0.25 and q=0.1 both give k=2, the identical
   draw. Reporting both would double-count one measurement as two independent q outcomes, which
   P1 and P2 assume are distinct. The probe now records each distinct k once, at the highest q
   that produces it, and says so in its log. No threshold, arm or dataset changed.

3. **Which q counts as "q = 0.1" for a narrow dataset.** The dedupe above means a dataset whose
   schema is narrow may have no distinct q = 0.1 measurement — at p = 8 the lowest distinct point
   is k = 2, recorded at q = 0.25. P1 and P2 are therefore evaluated at each dataset's **lowest
   distinct q**, and the scorer prints which q that was for every dataset so the substitution is
   visible rather than assumed. This is fixed now, before any registered number exists, because
   deciding it after seeing results would be choosing the test to fit the answer.

## Harness validation, appended 2026-09-08 14:25 (QA, not a registered outcome)

Sixteen datasets had landed and `cand_eicu_regime` was still running, so nothing below touches
the low-q question under test. This checks only that the probe reproduces known territory.

At q = 1.0 the probe's arms were compared against the committed `results/cand/*.csv` that the
sweep table is built from. Absolute AUPRCs track closely — the residual differences are what the
smaller cap (20,000 against 100,000) and the coarser resampling (3 folds against 5 seeds x 5
folds) predict — and **the sign of (hierarchy - imputation) agrees on 14 of 16**.

Both disagreements are at the noise floor and neither indicates a harness fault:

| dataset | probe hier / imp | sweep hier / imp | gap |
|---|---|---|---|
| cand_porto | 0.0506 / 0.0566 | 0.0611 / 0.0606 | ~0.005 at AUPRC 0.05, prevalence 3.6% |
| sweep_42136 | 0.9983 / 0.9984 | 0.9986 / 0.9985 | 1e-4 on a near-deterministic target |

This does not validate the low-q arms, which have no external reference — that is the point of the
experiment. It validates that the arms are wired to the estimators the papers use.

## AMENDMENT, 2026-09-08 14:40 — a permuted-mask null, registered before any result was scored

**The gap.** As written this design has no null. Every other result in this corpus carries one,
and Paper 3's whole bound exists to make the point that an excess smaller than the spread of its
own null means nothing. If P1 held I would have no answer to "against what?", and a gain from a
flexible estimator handed a meaningless partition is exactly the artefact a null catches.

Registered now, before `score_lowq.py` has been run even once. `cand_eicu_regime` was still
running and sixteen result files existed but had not been scored; the only numbers seen were the
q=1.0 harness-validation cells, which are the full-schema regime and say nothing about low q.

**The null.** `probe_lowq.py --permute S` row-permutes the mask with seed S before anything else
(`run_candidate.permute_mask`, the function Paper 3's bound uses), preserving each column's
marginal missingness rate while destroying the pattern. Every arm, q value and fold is otherwise
identical. Seeds 0, 1, 2 on all 17 datasets.

**P1 is tightened, not relaxed.** It now requires, at each dataset's lowest distinct q, all of:

  (a) paired median (family_cv - mean_indicator) >= +0.002, and
  (b) p < 0.05, and
  (c) the real median **exceeds the largest of the three permuted medians**,

on at least 3 of the 4 protocol-driven datasets. (a) and (b) are unchanged; (c) is added. A gain
that does not clear its own null does not count, whatever its p value.

**P5, new — the negative control.** Under a permuted mask the pattern carries nothing, so the
hierarchy has no structure to exploit. Across all 17 at every q, the permuted median
(family_cv - mean_indicator) must be below +0.002 on at least 14. **If P5 fails the contrast is
uninterpretable and LOWQ is withdrawn entirely** — it would mean the estimator manufactures a gain
from a meaningless partition, and no real-mask number from this design could be trusted.

P4 is unchanged and still refers to the real mask.

**Reporting.** The null is reported whatever happens, including if P1 fails, because "the real gain
did not clear a null that was itself near zero" and "the real gain did not clear a large null" are
different findings and the second would say the estimator is unstable at low q.

Output rows now carry a `permuted` column (-1 for the real mask). The sixteen files already on
disk predate it; the scorer reads a missing column as -1.

## OUTCOME, 2026-09-08 17:40 — P5 fails and LOWQ is WITHDRAWN

All 17 real-mask datasets and all 51 permuted runs completed, 0 failures, no truncated files.
Scored once, with `experiments/score_lowq.py`.

| prediction | verdict | |
|---|---|---|
| P1 | **FAILS** | (a)+(b)+(c) on 1 of 4 protocol-driven (`cand_mimic4_regime`); needs 3 |
| P2 | HOLDS | gain larger at the lowest q than at q=1.0 on 4 of 4 |
| P3 | **FAILS** | structural gain below +0.002 at every q on 2 of 6; needs 5 |
| P4 | **FAILS** | real gain below +0.002 on 10/16 at q=0.1, 11/17 at 0.25, 13/17 at 0.5, 12/17 at 1.0; needs 14 |
| **P5** | **FAILS** | worst permuted median below +0.002 on **10/16 at q=0.1**, 14/17 at 0.25, 15/17 at 0.5, 15/17 at 1.0 |

**The registered consequence of P5 fires: the contrast is uninterpretable and LOWQ is withdrawn
entirely.** The estimator shows a gain under a mask that carries no information by construction.

### What the null actually did

Datasets whose *permuted* gain reaches +0.002, by q:

| q | count | |
|---|---|---|
| 0.1 | **6 of 16** | acs_income, airbnb, eicu_regime, 42136, 46654, 46703 |
| 0.25 | 3 of 17 | nhanes, 42093, 46654 |
| 0.5 | 2 of 17 | nhanes, 46654 |
| 1.0 | 2 of 17 | nhanes, 46654 |

The null is well behaved everywhere except the narrowest schema. At q = 0.1, where roughly five
columns survive, several real "gains" are matched or beaten by their own null:

| dataset | real | worst null | median null |
|---|---|---|---|
| cand_acs_income | +0.0019 | **+0.0026** | +0.0020 |
| cand_airbnb | +0.0006 | **+0.0037** | +0.0034 |
| sweep_46654 | +0.0073 | +0.0042 | +0.0014 |
| sweep_46703 | −0.0000 | **+0.0029** | +0.0015 |
| cand_eicu_regime | −0.0022 | **+0.0028** | +0.0017 |

### The finding that survives the withdrawal, and it is about method

**At a five-column schema the estimator's own variance produces gains of up to +0.004 from a
partition that carries nothing.** The +0.002 floor this project uses throughout — in SWEEP, in
the oracle bound, here — is *below the noise floor of this estimator at that schema size*. A
decision threshold calibrated at full schema does not transfer to a narrow one.

That is a real result and it is not the one the design was aiming at. It also explains P4's
failure without any appeal to the hierarchy: the real-mask gains above +0.002 at q = 0.1 are the
same phenomenon as the permuted ones, and there are the same number of them (10 of 16 below the
floor in both conditions).

### What is NOT claimed

Nothing about whether the containment hierarchy pays at low q. The experiment cannot answer it,
because the instrument does not resolve an effect of that size at that schema width. The question
is not closed; it is **unmeasured by this design**. A future attempt needs either many more folds
and draws at low q, or a floor calibrated per schema width from the null rather than fixed at
+0.002 — and the null must be run first, not after.

The registered dichotomy also broke: P1 and P4 were written so that exactly one must hold, and
neither did. That is recorded rather than smoothed over.

### A defect in the scoring, found before reporting

`score_lowq.py` was written against the design as first registered and never updated when the
null amendment was added at 14:40 — it implemented P1(a) and P1(b) but not P1(c), and P5 not at
all. Its first run therefore reported four predictions and a verdict while silently omitting the
withdrawal condition. Caught by checking the output against the amendment before writing anything
up, and the eighth instance today of the same class: a check that is registered but not wired up
looks exactly like a check that passed. P1's verdict is unaffected — (c) can only tighten it.
