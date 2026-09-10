# PREVMATCH: removing the residual confound from Paper C's partition claim (registered 2026-09-07 12:5x)

## Why this must be run

Paper C's Section 10 names one confound as the limit on what may be concluded from its partition
result, and states it as unremovable:

> "What remains uncontrolled there is prevalence: equalising site size across carvings shifts the
> outcome rate between $0.269$ and $0.396$, because different groupings retain different people.
> Across five partitions the rank correlation between prevalence and benefit is $-0.70$ on five
> points, which cannot be dismissed. ... Rows, site size and prevalence cannot be held fixed
> simultaneously across different partitions of one population."

The last sentence is true only if every row is kept. Subsampling each site **stratified on the
outcome** fixes all three at once, at the cost of rows. `experiments/acs_repartition.py` gained a
`--prevalence` option today which does exactly that, and the build is verified: all five carvings
come out at exactly 500 records per site and exactly $0.330$ prevalence.

A rank correlation of $-0.70$ on five points is the single most quotable objection to Paper C's
central claim that the carving decides whether merging helps. This run either removes it or
establishes that the claim was prevalence after all.

## Design

Five carvings of the same $1{,}664{,}500$ ACS respondents — state, PUMA, occupation, industry,
education — each with

* every kept site subsampled to exactly **500** records (site size fixed),
* those 500 drawn stratified on the outcome to exactly **0.330** prevalence (outcome rate fixed),
* exactly **18** sites kept, drawn at random under the seed (site count fixed; 18 is education's
  surviving count and therefore the binding constraint),

at **five seeds**, because one draw of 18 sites is one sample. Merge decisions are then scored by
`experiments/gate_baselines.py` at 5 inner seeds, exactly as the published carving comparison was.
Surviving site counts before the site-count cap are education 18, state 51, industry 226,
occupation 278, PUMA 669.

## What is already seen, and disclosed

Only the build: the five matrices construct, at the stated sizes and rates. **No merge decision has
been scored on any prevalence-matched matrix.** The predictions below are blind. The published
size-matched numbers are the ones in Section 6 of Paper C, with the economic partition placing third
of five and the spread between the two geographic extremes as wide as anything between the types.

## Predictions

P1. Realised prevalence is $0.330 \pm 0.001$ in all five carvings, and every site holds exactly 500
    records. This is a build check and must pass or nothing else is interpretable.
P2. The spread in mean benefit across the five carvings, at matched prevalence, is at least half the
    spread reported at matched size only. That is: removing the prevalence confound does not remove
    most of the carving effect.
P3. The rank correlation between a carving's realised prevalence and its benefit is undefined or
    near zero, since prevalence is now constant by construction. Sanity check on the design.
P4. The ordering of the five carvings by benefit agrees with the published size-matched ordering on
    at least three of the five positions, averaged over seeds.
P5. Between-seed variation in each carving's benefit is smaller than the between-carving spread, so
    the ordering is a property of the carving and not of which 18 sites were drawn.

## Withdrawal

(a) P1 fails: the build is wrong and nothing may be read from the run.
(b) **P2 fails**: most of the apparent carving effect was prevalence. Paper C's partition claim is
    then substantially weaker than written, Section 6 must be rewritten, and the abstract sentence
    "Whether merging helps is set by how the federation is carved" must be qualified. This is a real
    possible outcome and it is why the run is worth doing.
(c) P5 fails: 18 sites is too few for a carving's benefit to be estimated, and the run is reported
    as underpowered rather than reinterpreted at a larger site count.

The comparison is registered once. Whatever it returns is what Paper C reports.

## Outcome (2026-09-07 12:2x; 5 carvings x 5 seeds, 26,750 decisions; scorer `experiments/score_prevmatch.py`)

**P1, P2, P3 and P5 held. P4 failed, and it is recorded as a failure.**

P1: all 25 matrices came out at exactly 500 records per site, exactly 18 sites, prevalence $0.3300$.

Mean benefit, with rows, site size, site count **and** outcome rate all fixed:

| carving | matched prevalence | between-seed s.d. | published, prevalence uncontrolled |
|---|---|---|---|
| education | $+0.0072$ | $0.0025$ | $+0.0078$ |
| state | $+0.0067$ | $0.0026$ | $+0.0049$ |
| PUMA | $+0.0072$ | $0.0032$ | $+0.0034$ |
| industry | $-0.0020$ | $0.0048$ | $-0.0024$ |
| occupation | $-0.0027$ | $0.0050$ | $-0.0029$ |

**P2 held, and by much more than the registered margin.** The spread across carvings is $0.00992$
at matched prevalence against $0.01070$ published without it — $93\%$ of the original, where the
prediction asked only for half. The residual confound named in Section 10 does not explain the
partition effect. The paper's own key pair is now exact rather than approximate: industry gives
$-0.0020$ and PUMA $+0.0072$ at **identical** prevalence, site size and site count, and the sign of
the benefit still reverses.

**P4 failed.** The published ordering agrees on 2 of 5 rank positions, not the 3 predicted. The
failure is confined to the three helping carvings, whose means sit within $0.0005$ of one another —
well inside a between-seed standard deviation of $0.0025$ to $0.0032$ — so their relative order is
not identifiable at this precision and should not have been predicted. The helps-against-harms split
is unaffected: the gap between the weakest helper and the strongest harmer is $+0.0087$, and the
within-group spreads are $0.0005$ and $0.0007$. No withdrawal condition attaches to P4.

### The precision caveat, stated rather than buried

Fixing four things at once costs rows: 9,000 per carving against the $1{,}664{,}500$ available. On
the seed-averaged means the helps-against-harms split is clean, but on individual seeds it is not.
It holds on 2 of 5 draws; on the other three, industry or occupation lands just above zero
($+0.0002$ to $+0.0017$) rather than below it. The two harming carvings are near zero and a single
draw of 18 sites can put them either side. `prereg/PREVMATCH2.md` adds seeds for precision only.

**What Paper C may say now.** Section 10's residual confound is removed by measurement rather than
argued away. The sentence "Rows, site size and prevalence cannot be held fixed simultaneously across
different partitions of one population" is false as written and must be replaced: they can be, by
subsampling each site stratified on the outcome, and when they are, the carving effect survives at
$93\%$ of its size.
