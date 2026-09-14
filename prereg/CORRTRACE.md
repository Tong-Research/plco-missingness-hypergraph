# CORRTRACE — can the indicator-to-value correlation figures be reproduced?

**Written 2026-09-10 11:35, BEFORE any measurement.**

## Why

Two manuscripts state, in their results sections, a measurement with four numbers and no macro
behind it:

> "the median absolute correlation between an indicator and a value runs $0.004$, $0.007$ and
> $0.010$ as the regime strengthens, while the same correlation computed inside a hospital stays at
> $0.038$, which is the noise floor of a single hospital and does not move at all."

`paper-missingness-assumptions/sections-results.tex:118` and
`paper-missingness-regimes/sections-results.tex:246`.

Every other number in these papers is generated into `tables/*.tex` and recomputes on demand. These
four are typed. On 2026-09-10 I searched every result subdirectory the two papers' generators read
and every experiment script computing a correlation, and could not find what produced them. That is
not evidence they are wrong. It is evidence that nobody can check them, which for a stated
measurement in a submitted paper is its own defect.

## Design

`experiments/probe_corrtrace.py`. The published simulation setup of `probe_mvpcdet.py`, unchanged:
`substrate()` for the transplanted mask and hospital ids, `random_dag(rng)` with
`rng = default_rng(1000 + rep)`, `N = 20,000` rows sampled without replacement, the **aligned**
mask, **no self-masking**, and `simulate(default_rng(2000 + rep), A, order, gamma, zid, mask, False)`.
Regime strengths gamma in {0.0, 1.0, 2.0}. **20 replicates**, matching the 20 in `results/mvpcdet/`
and `results/misdiag/`.

For each replicate and gamma:

- **Pooled**: over every (indicator j, value k) pair with j != k, the Pearson correlation between
  the indicator `isnan(Xm[:, j])` and the value `X[:, k]`, on all 20,000 rows. Report the median of
  the absolute values.
- **Within hospital**: the same quantity computed inside each hospital and pooled by taking the
  median over all (hospital, j, k) triples.

Indicator columns with no variation are skipped and their count reported; a correlation is undefined
there, not zero.

The interpretation the paragraph gives is that within a hospital the mask is independent of the
values *by construction*, so the within-hospital figure is estimation noise, and that the pooled
figure is a real association that grows with the regime.

## Predictions

- **C1.** The pooled median rises monotonically with gamma across 0.0, 1.0, 2.0.
- **C2.** The three pooled medians round to $0.004$, $0.007$ and $0.010$ at three decimal places.
- **C3.** The within-hospital median is larger than every pooled median, and rounds to $0.038$.
- **C4.** The within-hospital median does not move with gamma: its range across the three regime
  strengths is below $0.001$.

## Withdrawal and reporting

- If **C2 or C3 fails** while **C1 and C4 hold**, the qualitative claim survives and the four printed
  numbers do not. The sentence is then rewritten around the numbers this run produces, generated as
  macros like every other number in those papers, and the discrepancy is reported by name.
- If **C1 fails**, the claim that the association grows with the regime is not reproducible under the
  published setup, and the sentence is withdrawn from both papers rather than re-fitted.
- If **C4 fails**, "does not move at all" is withdrawn.
- If every prediction holds, the numbers are confirmed and generated as macros so they can never
  again be untraceable.

A mismatch may be **definitional** rather than an error: the sentence does not say which pairs it
ranges over. The definition tested here is fixed above, before any number exists, and any mismatch
will be reported as "under this definition" rather than as a refutation.

No prediction, threshold or definition is changed after the first number exists.

## Outcome (scored 2026-09-10)

C1 held, C4 held, C2 and C3 failed — the branch this document registers as "the qualitative claim
survives and the four printed numbers do not". Twenty replicates, `results/corrtrace/`.

| scope | printed | measured (median) | range over replicates |
|---|---|---|---|
| pooled, gamma 0 | 0.004 | 0.00512 | 0.00312 – 0.00725 |
| pooled, gamma 1 | 0.007 | 0.00973 | 0.00567 – 0.02001 |
| pooled, gamma 2 | 0.010 | 0.01586 | 0.00803 – 0.03481 |
| within hospital | 0.038 | 0.04232 | 0.03977 – 0.04467 |

The registered remedy was applied without modification: both sentences were rewritten around the
measured values, generated as macros (`\CtReps`, `\CtPoolZero`, `\CtPoolOne`, `\CtPoolTwo`,
`\CtWithin`), and the discrepancy is reported by name as Result 229 in `papers/MULTISITE-BENCHMARK.md`.

The mismatch is **not** definitional, which this document allowed for. Two alternative definitions
were tested after scoring and neither explains it: zero-variance indicator columns cannot affect the
pooled figure because pooled skips none of them, and correlating against observed rather than
complete values moves the numbers further away. The printed values behave like a single unreplicated
draw that landed low — three of four lie inside the replicate range, all four at its bottom, and
0.004 is below the sampling noise floor the stated design can produce at n = 20,000.

No prediction, threshold or definition was changed after the first number existed.
