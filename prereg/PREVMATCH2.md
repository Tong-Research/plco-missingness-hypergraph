# PREVMATCH2: more seeds, for precision only (registered 2026-09-07 12:3x)

## Why

`prereg/PREVMATCH.md` established the point of the experiment: with rows, site size, site count and
outcome rate all fixed, the spread in mean benefit across five carvings is $0.00992$ against
$0.01070$ with prevalence uncontrolled. That is the result and it is not re-litigated here.

What five seeds cannot settle is whether the two harming carvings are reliably negative. Their
between-seed standard deviations are $0.0048$ and $0.0050$ against means of $-0.0020$ and $-0.0027$,
and the helps-against-harms split reproduces on only 2 of 5 individual draws. This run adds seeds so
that the standard error of each carving's mean falls by about a third. Nothing else changes.

## What is already seen, and disclosed

Everything from the first run: the five means ($+0.0072$, $+0.0067$, $+0.0072$, $-0.0020$,
$-0.0027$), their between-seed standard deviations, the spread of $0.00992$, the 2-of-5 rank
agreement, and the per-seed sign instability. This is an extension for precision, not a blind test,
and its predictions are calibrated to those numbers.

## Design

Identical to PREVMATCH — same builder, same cap of 500, same target prevalence $0.330$, same 18
sites, same scorer — at **seeds 5 to 19**, which have never been drawn. Combined with the first five,
that gives 20 seeds per carving. Reported on the combined 20 seeds, with the first five identified.

## Predictions

Q1. On 20 seeds the spread across carvings is at least $0.006$, so P2's conclusion survives the
    added precision. This is the only prediction that could overturn anything.
Q2. Education, state and PUMA all have positive mean benefit; industry and occupation both negative.
Q3. The 95 per cent interval for the gap between the weakest helper and the strongest harmer
    excludes zero.
Q4. The three helping carvings remain within $0.002$ of one another, confirming that P4's failure was
    a tie and not a reordering.

## Withdrawal

(a) Q1 fails: the spread was a small-sample artefact of five seeds and PREVMATCH's conclusion is
    withdrawn along with it. Paper C then keeps Section 10's confound as an open limitation.
(b) Q2 fails for a carving whose sign flips with more data: that carving is reported as
    indistinguishable from zero rather than as helping or harming, and the paper says so.

Registered once. Whatever 20 seeds return is what Paper C reports, and no further seeds will be added
to this comparison.

## Outcome (2026-09-07 12:4x; 20 seeds, 100 runs; scorer `experiments/score_prevmatch2.py`)

**All four predictions held.** The conclusion of PREVMATCH stands, and is now measured with
intervals rather than asserted from five draws.

| carving | mean benefit, 20 seeds | 95% interval | five seeds alone |
|---|---|---|---|
| state | $+0.00741$ | $[+0.00637, +0.00834]$ | $+0.0067$ |
| PUMA | $+0.00679$ | $[+0.00560, +0.00793]$ | $+0.0072$ |
| education | $+0.00582$ | $[+0.00494, +0.00676]$ | $+0.0072$ |
| industry | $-0.00124$ | $[-0.00347, +0.00088]$ | $-0.0020$ |
| occupation | $-0.00396$ | $[-0.00593, -0.00189]$ | $-0.0027$ |

Q1: the spread is $0.01137$, against $0.01070$ published with prevalence uncontrolled. Removing the
confound does not shrink the carving effect. It is fractionally **larger** once prevalence is fixed.
Q2 held on the means. Q3: the gap between the weakest helper and the strongest harmer is $+0.00706$,
95 per cent interval $[+0.00508, +0.00904]$. Q4: the three helpers span $0.00159$, which confirms
that PREVMATCH's P4 failure was a tie and not a reordering.

### One qualification the intervals force, and the paper must carry it

**Industry is not distinguishable from zero** at 20 seeds: $-0.00124$ with an interval of
$[-0.00347, +0.00088]$. Occupation is clearly negative and the three helpers are clearly positive,
so the split is real, but the published sentence built on the industry–PUMA pair should be stated as
a *difference* rather than as a sign reversal. Paired seed by seed, PUMA minus industry is
$+0.00803$ with an interval of $[+0.00563, +0.01045]$, positive on 19 of 20 draws. State minus
occupation is $+0.01137$, $[+0.00925, +0.01356]$, positive on 20 of 20.

The claim Paper C may make is therefore: at identical rows, site size, site count and outcome rate,
which carving is used moves the mean benefit by about one point of AUPRC, from clearly helping to
not helping. That is stronger than what the paper currently claims, because it no longer rests on an
uncontrolled prevalence, and it is more careful, because one of the two harming carvings is not
individually separable from zero.

The five-seed means differ from the twenty-seed means by up to $0.0014$, which is the size of the
noise PREVMATCH warned about. The twenty-seed numbers supersede them.
