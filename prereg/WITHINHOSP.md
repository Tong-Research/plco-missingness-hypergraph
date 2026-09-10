# WITHINHOSP: is the indicator dependence a between-hospital artefact? (registered 2026-09-07 11:2x)

## Why this must be run

Paper A's first result is a dissociation: a panel's presence is predicted well by the other panels'
presences and badly by the always-observed values. The obvious referee objection is that the
dependence is an artefact of pooling heterogeneous hospitals — that panels look correlated only
because hospital A orders one set and hospital B another, and that within any one hospital there is
nothing left. Paper A currently has no answer. The latent-class result is suggestive in the other
direction (adjusted mutual information against the hospital is $0.382$, well short of 1) but it is
not the test.

## What is already seen, and disclosed

A pilot at `--min-rows 3000` on eICU, which keeps **3 of 100 hospitals** and 30 panels, gave medians
over panels:

| quantity | median AUROC |
|---|---|
| pooled fit, all holdout rows (`panels_tree` as published) | 0.967 |
| always-observed values, all holdout rows | 0.521 |
| pooled fit, evaluated on one site's holdout rows | 0.992 |
| **fit within a site, evaluated on that site's holdout rows** | **0.979** |

The predictions below were written with those four numbers in view. This is therefore a confirmation
at a wider site cut and on a second collection, not a blind test, and it is labelled as such.

## Design

`experiments/probe_withinhosp.py`, unchanged from the pilot. Panels are defined **once on the pooled
dev half**, by the same Jaccard $\ge 0.9$ rule as `probe_rrstruct.py`, so that every site is scored on
the same panels and the comparison is not confounded by different panel definitions. Sites partition
rows and are never given to a model.

Two runs: eICU and MIMIC-IV, both at `--min-rows 1000`, which keeps 31 of 100 eICU hospitals. A site
contributes a panel only if it has at least 100 dev and 100 holdout rows and both classes present.

## Predictions

W1. On eICU at `--min-rows 1000`, the median within-site AUROC is at least $0.85$.
W2. It is within $0.10$ of the pooled-everywhere median, in either direction.
W3. The median within-site values AUROC stays below $0.60$, so the dissociation survives conditioning
    on the hospital.
W4. The same three hold on MIMIC-IV, with the within-site median at least $0.75$ there.
W5. At least 20 eICU sites contribute at least one panel.

## Withdrawal

(a) W1 fails: the dependence largely *is* the between-hospital regime. Paper A must then say so, the
    referee objection stands, and the latent-class section is rewritten around it. This is a real
    possible outcome and the paper changes either way.
(b) W3 fails: the values become informative within a site, which would mean the dissociation is
    itself a pooling artefact. That would be the most damaging outcome and would be reported.
(c) W5 fails: too few sites clear the row floor for the median to mean anything, and the run is
    reported as inconclusive rather than reinterpreted at a lower floor.

## What each outcome buys the paper

If W1–W4 hold, Paper A gains a direct answer to its most likely referee objection, and the
latent-class claim becomes precise: the class the mixture recovers is correlated with the institution
but is not the institution, because conditioning on the institution leaves the dependence intact.
If W1 fails, the paper's second contribution is weaker than currently written and must be restated.

## Outcome (2026-09-07 12:2x; scorer `experiments/score_withinhosp.py`)

**All seven predictions held.**

| | eICU (31 sites, 30 panels) | MIMIC-IV (8 sites, 22 panels) |
|---|---|---|
| pooled fit, all holdout rows | 0.967 | 0.954 |
| values, all holdout rows | 0.521 | 0.561 |
| pooled fit, evaluated per site | 0.985 | 0.945 |
| **fit within a site** | **0.934** | **0.920** |
| values, evaluated per site | 0.521 | 0.522 |

The dependence does not collapse when the hospital is held fixed. On eICU it falls from $0.967$ to
$0.934$, and on MIMIC-IV from $0.954$ to $0.920$ — a few hundredths, not the collapse toward $0.5$
that a pure between-hospital artefact would produce. The values stay at chance within a site, so the
dissociation itself survives conditioning as well.

**What Paper A may now say.** The indicator dependence is not an artefact of pooling heterogeneous
hospitals, which is the paper's most likely referee objection and one it currently cannot answer.
It also makes the latent-class claim precise: the class the mixture recovers is correlated with the
institution (purity $5.82\times$ majority, adjusted mutual information $0.382$) but is not the
institution, because conditioning on the institution leaves the dependence essentially intact. The
regime is the ordering protocol, and hospitals share protocols.
