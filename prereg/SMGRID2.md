# SMGRID2: confirmation on fresh seeds, with the statistic the design should have used
# (registered 2026-09-07 12:1x)

## Why there is a second registration

`prereg/SMGRID.md` set its main threshold on a single grid cell whose standard error is about $0.3$
indicators. The cell at $\gamma = 1$, $s = 0.60$ returned $1.95$ against a required $2.0$, so S1
failed and nothing was claimed. The design was right and the threshold was wrong. This run repeats it
on seeds that have never been used, with the pooled statistic and thresholds set from the first run's
numbers, which are disclosed in full below and in `prereg/SMGRID.md`.

## What is already seen, and disclosed

Seeds 0 to 19 gave, for `n_detect_clean` aligned minus control, pooled over the four values of $s$:
$0.19 \pm 0.11$ at $\gamma = 0$, $2.08 \pm 0.15$ at $\gamma = 1$, $2.84 \pm 0.19$ at $\gamma = 2$.
Per-cell values are tabulated in `prereg/SMGRID.md`. The positive control ran
$0.43 \to 3.30 \to 4.02 \to 5.48$. The slope of the gap on $s$ at $\gamma = 1$ was $-0.248$ per unit.
Everything below was written with those numbers in view. This is a confirmation, not a blind test.

## Design

`experiments/probe_smgrid.py`, unchanged, on replicates **20 to 59** — 40 seeds, none used before.
Same substrate, same twelve columns, same six-of-twelve self-masking split rule, same grid, same
pinned `causal-learn` 0.1.4.7.

## Predictions

Each is on the mean over the four values of $s$, with a 95% interval from the replicate-level
standard error, which is the level at which the design has power.

T1. At $\gamma = 1$ the pooled gap is at least $1.5$, and its 95% interval excludes zero.
T2. At $\gamma = 0$ the pooled gap is at most $0.75$, and its 95% interval includes zero. Null control.
T3. The pooled gap at $\gamma = 2$ exceeds the pooled gap at $\gamma = 1$.
T4. Positive control: closed-mask detections on the six self-masked columns increase from
    $s = 0$ to $s = 0.60$ by at least $3.0$ indicators.
T5. At $\gamma = 1$ the gap at $s = 0.60$ is at least $1.2$, so the effect survives saturating the
    other half of the columns with genuine self-masking. This is the claim the paper needs, stated at
    a threshold the first run's precision can actually support.
T6. The regression slope of the gap on $s$ at $\gamma = 1$ is between $-1.5$ and $+1.5$ per unit,
    so the regime's contribution is flat in the self-masking strength rather than being eaten by it.

## Withdrawal

(a) T1 or T5 fails: the regime's contribution is not separable from a genuine signal at a threshold
    this design can support. Paper B keeps its scope condition exactly as written, and both this file
    and `prereg/SMGRID.md` are cited in the paper as the attempt that did not succeed.
(b) T2 fails: the aligned and control arms differ in something other than the regime, and MISDIAG's
    published result needs re-examination. This is the outcome that would cost the most.
(c) T4 fails: the step is not detecting genuine self-masking, so the clean-versus-self-masked split
    is not measuring what it claims and the design is void.

No further registration of this comparison will be written. If T1 to T6 hold, the result is used; if
they do not, the attempt is reported as a negative and the question is closed for this paper.

## Outcome (2026-09-07 12:3x; 40 replicates, seeds 20-59; scorer `experiments/score_smgrid2.py`)

**All six predictions held on seeds never used before.**

`n_detect_clean`, aligned minus control, over the six columns that never self-mask:

| $\gamma$ | $s=0$ | $s=0.15$ | $s=0.30$ | $s=0.60$ | pooled (95% CI) |
|---|---|---|---|---|---|
| 0 | $-0.02$ | $0.05$ | $0.00$ | $-0.12$ | $-0.025$ $[-0.16, +0.11]$ |
| 1 | $2.00$ | $2.02$ | $2.02$ | $1.98$ | $+2.006$ $[+1.79, +2.22]$ |
| 2 | $2.95$ | $2.68$ | $2.95$ | $2.58$ | $+2.788$ $[+2.59, +2.98]$ |

Positive control, closed mask, six self-masked columns: $0.53 \to 3.36 \to 3.82 \to 5.27$.
Slope of the gap on $s$ at $\gamma = 1$: $-0.052$ per unit, so the regime's contribution is flat in
the self-masking strength across the whole range.

The estimates reproduce seeds 0-19 closely ($2.006$ against $2.075$ at $\gamma = 1$; $2.788$ against
$2.837$ at $\gamma = 2$), and the null control is now exactly on zero with a tight interval.

**What Paper B may now say.** The regime manufactures false detections whether or not a genuine
value-driven signal is present. On columns that never censor themselves, an institutional regime at
the strength measured in real eICU makes the detection step report a parent for two more indicators
than the closed-missingness control, and that number does not move when the other half of the
columns are saturated with real self-masking. The scope paragraph in Section 5 is replaced by this,
and both `prereg/SMGRID.md` (the failed first attempt) and this file are cited.
