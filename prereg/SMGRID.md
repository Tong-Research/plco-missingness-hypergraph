# SMGRID: separating the regime from a genuine self-masking signal (registered 2026-09-07 11:4x)

## Why this must be run

Paper B's second result is that an institutional regime makes MVPC's detection step report
value-driven missingness that does not exist. The paper then states its own boundary: with partial
self-masking added, the aligned and control conditions give $7.90$ and $7.45$, "the extra
contribution of the regime is no longer separable from the signal that is genuinely there", and
"separating the two would need a design in which the strength of the self-masking and the strength of
the regime are varied independently, which we did not run."

That sentence invites the referee question the paper cannot answer. This run answers it.

## Design

The flaw in MISDIAG's secondary condition was that self-masking was switched on for *every* column,
so once a real signal existed the step found it everywhere. `experiments/probe_smgrid.py` gives
self-masking to **six of the twelve columns**, drawn once per replicate from a seed fixed before any
outcome is read, and recorded in every row. On the other six, under an aligned transplanted mask,
every reported parent remains a false positive at every self-masking rate, because the transplanted
mask is independent of the simulated variables within a hospital by construction.

Grid: $\gamma \in \{0, 1, 2\}$ by $s \in \{0, 0.15, 0.30, 0.60\}$ by $\{$aligned, closed$\}$, giving
24 cells per replicate. Substrate, columns, regime anchor, control and alpha are identical to
PLASMODE and MISDIAG. `causal-learn` is pinned at 0.1.4.7 on all four workers, verified today.

The headline is `n_detect_clean`, the number of the six never-self-masking columns for which the step
reports a parent, and specifically its aligned-minus-control difference. The self-masked six carry a
positive control: under the closed mask their detections should rise with $s$, because there the
signal is real and there is no regime.

## What is already seen, and disclosed

One pilot replicate (rep 900, not in the analysis set) gave for `n_detect_clean`, aligned minus
control: $0, 0, 0, -1$ at $\gamma = 0$; $+2, +4, +6, +4$ at $\gamma = 1$; $+5, +6, +6, +5$ at
$\gamma = 2$, across $s = 0, 0.15, 0.30, 0.60$. The self-masked six under the closed mask went
$0 \to 4 \to 6 \to 6$ as $s$ rose. The thresholds below were chosen with those numbers in view, so
this is a confirmation on 20 unseen replicate seeds (0 to 19), not a blind test.

## Predictions

S1. At $\gamma = 1$, the aligned-minus-control difference in `n_detect_clean` is at least $2.0$ at
    **every** value of $s$, including $s = 0.60$.
S2. At $\gamma = 0$ that difference is at most $1.0$ at every $s$. This is the null control: with no
    regime, alignment cannot matter however much genuine self-masking exists.
S3. The difference at $\gamma = 2$ is larger than at $\gamma = 1$, averaged over $s$.
S4. Positive control: on the six self-masked columns under the **closed** mask, mean detections rise
    monotonically in $s$, and at $s = 0.60$ exceed $3.0$ of six.
S5. The difference in S1 does not fall by more than half between $s = 0$ and $s = 0.60$.

## Withdrawal

(a) S1 fails at any $s$: the regime's contribution is not separable after all, the boundary stated in
    the paper stands as written, and nothing is added. Paper B keeps its current scope condition.
(b) S2 fails: alignment matters without a regime, which would mean the aligned and control arms
    differ in something other than the regime, and the whole MISDIAG result would need re-examining.
    This is the outcome that would cost the paper the most and it is the reason S2 is registered.
(c) S4 fails: the step is not detecting genuine self-masking, so the "clean versus self-masked"
    split is not measuring what it claims and the design is void.

## What this buys the paper

If S1 to S5 hold, the scope paragraph in Section 5 is replaced by a two-factor result with a null
control and a positive control, and Paper B can say that the regime manufactures false detections
*whether or not* a genuine value-driven signal is present. If S1 fails, the paper is unchanged and
the negative is recorded here.

## Outcome (2026-09-07 12:0x; 20 replicates, seeds 0-19; scorer `experiments/score_smgrid.py`)

**Four of five predictions held. S1 failed, and it is recorded as a failure.**

`n_detect_clean`, aligned minus control, over the six columns that never self-mask:

| $\gamma$ | $s=0$ | $s=0.15$ | $s=0.30$ | $s=0.60$ |
|---|---|---|---|---|
| 0 | 0.30 | 0.20 | 0.05 | 0.20 |
| 1 | 2.00 | 2.30 | 2.05 | **1.95** |
| 2 | 2.85 | 2.70 | 2.75 | 3.05 |

S1 required at least $2.0$ at every $s$ when $\gamma = 1$. The cell at $s = 0.60$ came in at $1.95$,
so S1 fails as registered, and by withdrawal condition (a) nothing is claimed from this run and
Paper B keeps its scope condition as written.

S2 held: at $\gamma = 0$ the gap never exceeds $0.30$, so alignment does nothing without a regime.
S3 held. S4 held, and the positive control is clean: closed-mask detections on the six self-masked
columns run $0.43 \to 3.30 \to 4.02 \to 5.48$ as $s$ rises. S5 held.

### What the failure was, stated precisely

The threshold was set on single cells whose standard error is about $0.3$, so $2.0$ was inside the
noise. Pooled over $s$, which is the statistic the design should have registered, the gaps are
$0.19 \pm 0.11$ at $\gamma = 0$ (95% interval $-0.03$ to $0.41$), $2.08 \pm 0.15$ at $\gamma = 1$
($1.78$ to $2.37$) and $2.84 \pm 0.19$ at $\gamma = 2$ ($2.46$ to $3.22$), and the slope of the gap
on $s$ at $\gamma = 1$ is $-0.248$ per unit, which is $-0.15$ indicators across the whole range.

That is a registration error, not a result. The effect is not being claimed on the strength of a
prediction that failed. `prereg/SMGRID2.md` runs the confirmation on 40 fresh seeds with the pooled
statistic and thresholds set from these numbers, disclosed.
