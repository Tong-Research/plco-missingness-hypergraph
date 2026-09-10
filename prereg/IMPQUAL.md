# IMPQUAL: does the regime predict how imputation behaves? (registered 2026-09-07 13:0x)

## Why this must be run

Paper A's Implications section ends with a recommendation it never tested:

> "datasets should be labelled by their regime before they are used to benchmark imputation, because
> the two regimes make opposite demands."

Nothing in the paper measures imputation. Without this the recommendation is an inference from a
mechanism story, and a referee is entitled to say so. The paper is also, as it stands, descriptive:
it says what missingness is and not what an analyst should do differently.

## The prediction the mechanism makes

Where missingness is structural, a value is absent because of what the other values are, so the
observed values pin the missing one down and a method exploiting inter-column structure should beat a
column mean by a lot. Where it is protocol-driven, a value is absent because nobody ordered the
measurement, and given the regime the value itself is ordinary, so the observed values say less and
structured imputation should buy less.

## Design

`experiments/probe_impqual.py` on all \NDatasets{} datasets, three seeds each. On the holdout half we
take the entries that are actually observed and hide a random $10\%$ of them, so the hidden entries
have ground truth and the artificial mask is MCAR by construction — this measures imputability, not
the mechanism a second time. Four imputers: column mean, column median, 5-nearest-neighbour, and
MICE with a Bayesian ridge. Score is normalised RMSE on the hidden entries, median over columns.
Headline per dataset: the relative gain of the better of KNN and MICE over the column mean.

Groups are Paper A's own, fixed before this file: four protocol-driven datasets (eICU, MIMIC-IV,
NHANES, road safety) and six structural ones. The seven unclassified datasets are reported and
excluded from the test.

## What is already seen, and disclosed

Three datasets, one seed, run before this file was written:

| dataset | group | structured-over-mean gain |
|---|---|---|
| eICU | protocol-driven | $+0.293$ |
| ACS income | structural | $+0.107$ |
| OpenML 42737 | structural | $+0.815$ |

**These do not support the prediction cleanly.** ACS income is a structural dataset with a gain below
eICU's. The thresholds below are set with that in view, and the direction is not assumed.

## Predictions

I1. The median gain over the six structural datasets exceeds the median over the four
    protocol-driven datasets.
I2. The gap between those two medians is at least $0.10$.
I3. MICE or KNN beats the column mean on at least 14 of the \NDatasets{} datasets, so the comparison
    is between degrees of usefulness and not between a method that works and one that does not.
I4. The ordering is stable across the three seeds: the sign of I1 is the same on each seed
    separately.

## Withdrawal

(a) I1 fails: the regime does **not** predict imputability. Paper A's recommendation that datasets be
    labelled by regime before benchmarking imputation is then withdrawn and replaced with the
    narrower claim the data support, which concerns mask-aware methods and diagnostics rather than
    imputation accuracy. This is a real possible outcome — one of three pilot datasets already runs
    against it — and the paper will say so plainly.
(b) I2 fails while I1 holds: the effect exists but is too small to act on, and the recommendation is
    reported as directional rather than practical.
(c) I3 fails: NRMSE is not measuring imputation quality on these data and the run is void.

This comparison is registered once and will not be re-run with different groups or metrics.

## Outcome (2026-09-07 13:5x; 17 datasets x 3 seeds; scorer `experiments/score_impqual.py`)

**I1 failed, in the opposite direction, on every seed. The recommendation is withdrawn.**

Relative gain of the better of KNN and MICE over a column mean, averaged over three seeds:

| group | median gain | per dataset |
|---|---|---|
| protocol-driven (4) | $+0.317$ | eICU $+0.286$, MIMIC-IV $+0.365$, NHANES $+0.348$, road safety $+0.180$ |
| structural (6) | $+0.258$ | ACS $+0.105$, Airbnb $+0.459$, Higgs $+0.411$, ML42737 $+0.772$, ML46654 $+0.012$, ML46703 $+0.040$ |
| unclassified (7) | $+0.083$ | |

The structural median is **below** the protocol-driven median, by $0.059$. The prediction was that it
would be above it by at least $0.10$. The sign is wrong on all three seeds separately, so this is not
noise. I3 held: KNN or MICE beats the column mean on 17 of 17 datasets, so NRMSE is measuring
imputation quality and the comparison is between degrees of usefulness.

The structural group is also wildly heterogeneous, from $+0.012$ to $+0.772$. Whatever governs how
much structured imputation buys on these data, the missingness regime is not it.

### What changes in the paper

By withdrawal condition (a), the recommendation that "datasets should be labelled by their regime
before they are used to benchmark imputation, because the two regimes make opposite demands" is
**withdrawn**. It was an inference from a mechanism story and the measurement does not support it.
The Implications section is rewritten to make the narrower claim the data do support: the regime
label matters for diagnostics, which ask what determines missingness, and for methods that read the
mask. It does not predict how much a structured imputer beats a column mean.

The pilot disclosed in this file already pointed this way -- ACS income, a structural dataset, had a
gain below eICU's -- and the full run confirms it.
