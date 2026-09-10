# NOTREAT: does the dissociation survive without the treatment fields? (registered 2026-09-07 11:2x)

## Why this must be run

Paper A states the limitation itself: "the eICU and MIMIC-IV matrices were constructed to include
treatment fields. A missing treatment field means that the treatment was not given." That is a
different object from an unordered measurement, and a referee is entitled to ask whether the
indicator-indicator dependence is carried by those columns. The paper's current answer is that the
finding also holds on NHANES and the road-safety data, which have no such construction. That is
evidence but it is not the direct test, because those are different populations.

## Design

`experiments/probe_rrstruct.py` with the new `--drop-prefix`. On eICU the value is
`vent_,inf_,rrt_`, which removes **15 of 57** columns. MIMIC-IV carries the same fifteen treatment
fields under unprefixed names, so the value there is the explicit list
`peep,fio2,tidal_volume,set_resp_rate,plateau_pressure,mean_airway_pressure,minute_volume,
norepinephrine,epinephrine,vasopressin,phenylephrine,dopamine,dobutamine,insulin_infusion,rrt_hours`,
which also removes **15 of 57**. Both counts were checked against the matrices before this file was
frozen, and an earlier draft of this registration said 16 on eICU, which was wrong. Everything else is identical to the published run: same hash split, same Jaccard $\ge 0.9$
panels, same models, same dev/holdout direction. Run on both collections, and in the mirror
direction on eICU as well, since the published claim is stated as surviving split reversal.

## What is already seen

Nothing. No variant of this run has been executed. The published pooled numbers are
`panels_tree` $= 0.955$ at the maximum across datasets, with values near chance.

## Predictions

N1. On eICU without treatment columns, the median panel `panels_tree` AUROC is at least $0.80$.
N2. The median `values` AUROC stays below $0.60$.
N3. The gap `panels_tree` minus `values`, taken per panel and then median, is at least $0.20$.
N4. N1 to N3 also hold on MIMIC-IV.
N5. N1 to N3 also hold on eICU in the mirror direction.

## Withdrawal

(a) N1 fails: the dependence was carried by the treatment fields. Paper A's clinical evidence then
    rests on NHANES and road safety alone, the two intensive-care collections are reported as
    construction-dependent, and the limitation is promoted from a caveat to a result.
(b) N3 fails while N1 holds: the values become as informative as the panels once treatments are
    dropped, which would mean the dissociation is specific to treatment columns. Reported as such.
(c) The column filter removes a different count than 15 on either collection: the run is void and
    the prefixes are wrong.

## Outcome (2026-09-07 12:0x; scorer `experiments/score_notreat.py`)

**All nine predictions held.** Exactly 15 of 57 columns were removed on each collection, as required.
With every ventilator, infusion and renal-replacement field gone, 40 columns carry missingness and
the dissociation is unchanged:

| run | panels (median) | values (median) | per-panel gap (median) |
|---|---|---|---|
| eICU | 0.966 | 0.516 | 0.455 |
| MIMIC-IV | 0.949 | 0.553 | 0.391 |
| eICU, mirror direction | 0.973 | 0.516 | 0.455 |

The published pooled figure with the treatment fields present is $0.955$ at the maximum across
datasets, so removing them changes nothing that matters. The limitation stated in Paper A's
discussion — that the two intensive-care matrices were constructed to include treatment fields, and
that a missing treatment field means the treatment was not given — is now answered directly rather
than by appeal to NHANES and the road-safety data. The paragraph should be rewritten to say so.
