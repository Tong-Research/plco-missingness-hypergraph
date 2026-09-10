# PORTABLE — does any pre-merge signal have a threshold that ports between collections?

**Written 2026-09-08 18:20, BEFORE any measurement.** Runs on committed per-decision records.

## Why

Paper C's recommendation is that **the decision to join can be made from the site's own
aggregates**. Section~\ref{sec:selection} supports it by showing partner *selection* recovers at
most 4% of the oracle gap. That is evidence about ranking partners, not about the recommendation's
actual content, which is a claim about *what kind of quantity* a site can act on.

ADMIT (Result 218) found the sharper version by accident: schema complementarity improves the
admission decision within eICU by +0.006, and the threshold learned there admits **0 of 660**
MIMIC-IV decisions because it lies outside MIMIC's range. A complementarity threshold is not a
portable number.

This generalises that one observation into the test the recommendation deserves: **is
portability the property that separates a site's own aggregates from everything else?**

## Design

For each candidate signal, fit a threshold on the eICU development pools that maximises mean
benefit over admitted decisions, then apply that threshold unchanged to the MIMIC holdout pools
and measure the change in mean benefit. Same split, same pools and same degeneracy rule as ADMIT.

**Site-own aggregates** (computable by the target before it contacts anyone):
`epv_target`, `n_target`, `events_target`, `d_target`

**Joint signals** (require the partner pool):
`schema_jaccard` (and its complement), `ratio_partner_to_target`, `n_partner_total`, `n_min`,
`q_median`, `i2_median`

Reported per signal: the development threshold, the development delta, the holdout delta, the
admitted counts, and whether the threshold is inside the holdout's observed range at all.

## Predictions

- **P1.** Every site-own aggregate whose development delta is >= +0.002 keeps a holdout delta
  >= −0.002 (it does not actively harm), on both MIMIC holdout pools that are non-degenerate.
- **P2.** At least one joint signal has a development delta >= +0.002 whose threshold is
  **outside** the holdout's observed range, i.e. degenerate there. ADMIT already shows one; the
  prediction is that this is a property of joint signals rather than a quirk of complementarity.
- **P3.** The mean absolute holdout delta over site-own aggregates is smaller than over joint
  signals.

## Withdrawal and reporting

- If **P1 fails**, a site-own aggregate's threshold does not port either, and Paper C's
  recommendation needs qualifying rather than strengthening. Named per signal.
- If **P2 fails**, complementarity's non-portability is specific to it and Result 218 must not be
  generalised. The sentence added to Paper C on 2026-09-08 is narrowed accordingly.
- If **P3 fails**, portability does not separate the two kinds of signal and no general claim is
  made.
- A signal whose development delta is below +0.002 is reported but carries no prediction: there
  is no threshold worth porting.
- Degeneracy is reported as degeneracy, never as a delta. A rule admitting fewer than half the
  baseline's decisions does not count as a pass, as in ADMIT.

Thresholds are fitted on development only and never refitted on the holdout.

## OUTCOME, 2026-09-08 18:30 — P2's letter holds, its rationale fails, and P1/P3 are vacuous

| signal | kind | dev threshold | dev delta | holdout |
|---|---|---|---|---|
| `epv_target` | own | 0.2857 | +0.00000 | no effect |
| `n_target` | own | 86 | +0.00000 | no effect |
| `events_target` | own | 12 | +0.00000 | no effect |
| `d_target` | own | 25 | +0.00287 | +0.00000 on all three |
| `comp` | joint | 0.4118 | **+0.00597** | **DEGEN 285/1020; DEGEN 0/660, c outside [0, 0.405]**; +0.00038 |
| `ratio_partner_to_target` | joint | 2.887 | +0.01116 | +0.00058, +0.00208, +0.00020 |
| `n_partner_total` | joint | 1736 | +0.00619 | +0.00052, −0.00012, +0.00029 |
| `q_median` | joint | 74.25 | +0.00322 | +0.00139, −0.00180, +0.00085 |
| `i2_median` | joint | 0.9661 | +0.00156 | +0.00042, +0.00005, +0.00032 |

**P1 and P3 are vacuous and are not claimed.** Three of the four site-own aggregates have a
development delta of exactly zero, and `d_target >= 25` admits **1020/1020, 660/660 and 336/336**
of the holdout decisions — its zero holdout delta means the rule does nothing there, not that it
ports well. The mean absolute holdout delta for site-own signals (0.00000 against 0.00056 for
joint) is therefore an artefact of having no rule, and P3 "holding" says nothing.

**The cause is a flaw in this design, found on execution.** The probe only searches one-sided
`signal >= c` rules. For `epv_target` the useful direction is the *upper* bound that is already
the baseline gate, so no lower bound can help and the search returns nothing by construction.
A two-sided search would be needed to test site-own aggregates at all. Recorded rather than
patched after the fact.

**P2's letter holds and its rationale fails.** One joint signal — complementarity — has a real
development effect (+0.00597) and a threshold outside the holdout's range. But the prediction's
stated reason was that this would be *a property of joint signals rather than a quirk of
complementarity*, and the other four joint signals port perfectly well: `ratio_partner_to_target`,
`n_partner_total`, `q_median` and `i2_median` all transfer with small deltas and none is
degenerate.

### Consequence, and the withdrawal clause fires

Non-portability is **specific to complementarity**, not a property of quantities that involve the
partner pool. Per the clause, Result 218 must not be generalised and the sentence added to Paper C
earlier today is narrowed: its final claim — that site-own aggregates "are on the same scale
everywhere" — is unsupported by this experiment, which could not test them, and its framing of
complementarity's failure as following from being a joint signal is contradicted by four
counter-examples.

What survives is exactly what ADMIT measured: a complementarity threshold fitted on one corpus
does not apply to another, because the two corpora do not occupy the same range of that variable.
