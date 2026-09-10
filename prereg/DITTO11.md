# DITTO11: a personalised-federated-learning baseline that Paper C computes and does not report
# (registered 2026-09-07 15:0x)

## Why this must be run, and why it is uncomfortable

`gate_baselines.py` computes a Ditto arm \citep{li2021ditto} on every pool. Ditto is a standard
personalised-federated-learning baseline and it runs by default: it is populated in every decision
file we checked. **Paper C reports it nowhere.** Its Related Work mentions Ditto once, only to say
"we claim none of its machinery".

Paper C's abstract claims that adaptive shrinkage "takes the best mean ($31.8\%$ of attainable gain)
and the best worst case ($+10.9\%$), and is the only policy tested that is never negative on any
pool." That $+10.9$ is Freddie Mac partitioned by state, which is the worst pool in Table~4.

On the five pools where a Ditto arm is already committed, scored by Paper C's own convention (share
of the $\lambda$-oracle's gain over the local model, pools below $0.002$ attainable marked
unreadable), the three readable pools give:

| pool | adaptive shrinkage | Ditto |
|---|---|---|
| ACS, spanning | $40.9$ | $38.7$ |
| eICU | $48.5$ | $26.1$ |
| **Freddie Mac, state** | $\mathbf{10.9}$ | $\mathbf{25.1}$ |
| mean | $33.5$ | $30.0$ |
| worst | $\mathbf{10.9}$ | $\mathbf{25.1}$ |

Adaptive shrinkage wins the mean. **Ditto wins the worst case, on the paper's own worst pool, by
fourteen share points.** If that survives on all eleven pools, the abstract's "best worst case" is
wrong as written, and a referee who runs the repository's own code will find it.

This is registered before running the other eight pools.

## Design

`experiments/gate_baselines.py` unchanged, at 5 seeds, on the eleven matrices behind Table~4:
`acs_full_income`, `acs_ladder_10000`, `acs_ladder_5000`, `mimic4_sites`, `acs_span_traveltime`,
`mimic_sites_unit_x_system`, `freddiemac_propertystate`, `acs_span_income`, `lendingclub`,
`freddiemac_zip2`, `eicu_sites`. Scoring exactly as Table~4 does, so the new rows drop straight in.

## What is already seen, and disclosed

The five pools above, three of them readable. The other eight have never been scored with a Ditto
arm read out. The predictions below are set with the five in view.

## Predictions

D1. Over the eight pools whose attainable gain clears $0.002$, adaptive shrinkage still has the
    higher mean share than Ditto.
D2. Ditto's worst pool is better than adaptive shrinkage's $+10.9$.
D3. Ditto is negative on at least one pool, so adaptive shrinkage keeps "the only policy never
    negative anywhere".
D4. Ditto beats the fixed-weight policies and the gate on the mean, so it is a serious baseline and
    not a straw man.

## Withdrawal, and what each outcome costs the paper

(a) **D2 holds**: the abstract and Table~5 must be corrected. Adaptive shrinkage keeps "best mean"
    and loses "best worst case", and Ditto is added to Table~5 as a reported baseline. This is the
    expected outcome and it is why the run is being done before submission rather than after review.
(b) D2 fails: adaptive shrinkage keeps both claims, and the paper gains a strong personalised-FL
    baseline row it currently lacks. Nothing is corrected.
(c) D3 fails: Ditto is never negative either, and the uniqueness claim goes as well.
(d) D1 fails: Ditto beats adaptive shrinkage on the mean too, and the paper's recommendation itself
    has to be reconsidered. This is the outcome that would cost the most.

Whatever the eleven pools return is what Paper C reports.

## Outcome, provisional (2026-09-07 16:1x; 9 of 11 pools)

**D2 failed, and that is the good outcome: Paper C's abstract stands.** D1 and D3 held. D4 failed,
and the reason matters more than the verdict.

Policy summary over the six readable pools, in Paper C's own units:

| policy | mean | median | worst pool | pools below zero |
|---|---|---|---|---|
| **adaptive shrinkage** | **34.6** | **39.0** | **+12.3** | **0** |
| fixed $0.50$ | 28.4 | 34.3 | $-2.1$ | 1 |
| fixed $0.25$ | 24.0 | 24.3 | $+10.8$ | 0 |
| local validation | 18.9 | 17.7 | $+3.7$ | 0 |
| fixed $0.75$ | 13.6 | 39.3 | $-63.9$ | 2 |
| gate, fixed cut | 8.5 | 19.5 | $-54.0$ | 2 |
| **Ditto** | $-5.0$ | 16.9 | $-123.5$ | 2 |
| always merge | $-31.9$ | 13.7 | $-183.1$ | 3 |

D2 is settled whatever the two outstanding pools return: Ditto's worst is $-123.5$ on ACS TravelTime,
which is far below adaptive shrinkage's $+10.9$. The abstract's "best worst case" needs no correction.

### The correction to what this file predicted, and why the preview misled

The five-pool preview quoted above came from the `cut_dt_*` family, a different sweep over a narrower
pool set, and it showed Ditto **winning** the worst case by fourteen share points. On the eleven pools
behind Table~4 the ordering reverses completely. The preview was real but unrepresentative, which is
the reason this comparison was registered before conclusions were drawn rather than after.

### D4 failed, and it must not be reported as "Ditto is a weak baseline"

Ditto came second from last on the deployable mean. Attribution, which the project's standing rule
requires before any such statement is made:

| | mean | worst pool |
|---|---|---|
| Ditto, $\lambda$ from the inner split (deployable) | $-5.0$ | $-123.5$ |
| Ditto, $\lambda$ chosen on the test rows (an oracle it cannot have) | $\mathbf{69.7}$ | $+12.0$ |
| adaptive shrinkage, deployable | $34.6$ | $+12.3$ |

**Ditto's family beats adaptive shrinkage's realised performance by 35 share points when its strength
is chosen with an oracle.** The deployable arm cannot find that setting, and the gap is $74.7$ points.
That is a selection failure, not a method failure, and the paper must say so.

This strengthens Paper C rather than weakening it. The paper's contribution is a rule for choosing how
far to shrink from local data. Ditto shows that the interpolation family is capable and that choosing
its strength from a held-out local split is the hard part — which is exactly the problem Paper C's
rule solves. The honest sentence is not "we beat Ditto"; it is "a standard personalised-federated
baseline has a higher ceiling and no way to reach it from local data."

Outstanding: `freddiemac_propertystate` and `freddiemac_zip2`, both 32 GB jobs queued behind the one
node that can host them. `freddiemac_propertystate` is the pool that supplies adaptive shrinkage's
$+10.9$, so the final table waits for it.


## Final outcome (2026-09-07 21:5x; all 11 pools, 8 with a readable denominator)

Unchanged in every verdict. **D1 and D3 held; D2 and D4 failed.**

| policy | mean | median | worst pool | pools below zero |
|---|---|---|---|---|
| **adaptive shrinkage** | **31.7** | **35.7** | **+10.8** | **0** |
| fixed $0.50$ | 29.6 | 34.3 | $-2.1$ | 1 |
| fixed $0.25$ | 23.6 | 24.3 | $+10.8$ | 0 |
| fixed $0.75$ | 18.6 | 39.3 | $-63.9$ | 2 |
| local validation | 17.5 | 17.7 | $+1.9$ | 0 |
| gate, fixed cut | 10.0 | 19.5 | $-54.0$ | 3 |
| **Ditto** | 3.5 | 23.5 | $-123.5$ | 2 |
| always merge | $-19.0$ | 19.6 | $-183.1$ | 3 |

This scoring reproduces the published figures, which is the check that the convention was applied
correctly: the paper reports adaptive shrinkage at mean $31.8$ and worst $+10.9$ over its eight
readable pools; this run gives $31.7$ and $+10.8$.

**D2 failed and the abstract needs no correction.** Ditto's worst pool is $-123.5$ on ACS TravelTime.
The three-pool preview that opened this file, which showed Ditto winning the worst case, was drawn
from the wrong pool set.

One detail the preview did get right: on Freddie Mac partitioned by state, the pool that supplies
adaptive shrinkage's $+10.9$, **Ditto is the better policy at $22.6$ against $10.8$.** That is stated
in the paper.

**D4 failed, and the attribution is what goes in the paper.** With its regularisation strength chosen
on the scoring rows, Ditto reaches a mean of $77.1$ and a worst pool of $+12.0$ --- above adaptive
shrinkage's realised $31.7$. The deployable arm reaches $3.5$. The $73.6$-point gap is a selection
failure, not a failure of the family, and it is the problem Paper C's rule exists to solve.

### Written into the paper

Table~5 gains a Ditto row; Section~\ref{sec:policy} gains a paragraph giving both the deployable
result and the oracle, with the selection reading; Related Work now points at the policy section
rather than only citing Ditto. Paper C went from 34 to 35 pages, which matters only if Applied
Intelligence has a page limit --- still an open question.
