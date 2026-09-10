# SIMCONTROL: the control the oracle-bound paper proposes and records as not run
# (registered 2026-09-08 03:5x)

## Why

Paper 3's central explanation is that the standard way of simulating pattern heterogeneity
conflates two things: patterns differing in their coefficients, and patterns differing in the
conditional relationship between $X$ and $y$. It draws the outcome from each row's own pattern
coefficients, so divergence is predictive by construction and a positive result is close to
guaranteed. The paper then says, in its own limitations:

> "a design that separates the two is available and cheap: draw the per-pattern coefficients, but
> draw the outcome from a *fixed* coefficient vector ... We did not run that design, and we do not
> claim its result. We note only that it is the control which our own factorial lacked."

and, in Section~\ref{sec:missing-control}: "That is an argument plus one decisive dataset, not a
controlled demonstration, and we mark it as such."

This runs it. It is the difference between an argument and a demonstration, and it is the paper's
own design, not a new one.

## Design

`experiments/synthgen.py` gains `outcome_from`. Under `pattern`, the default and unchanged, the
outcome is drawn from `betas[assign[i]]`. Under `shared` the per-pattern coefficients are drawn
exactly as before --- so the realised coefficient spread is identical --- but the outcome is drawn
from the shared vector `beta0`. Patterns therefore still differ in what they measure and in their
populations, and no longer differ in the conditional relationship.

`run_synthetic_suite.py` gains `--outcome-from` and `--mechanism`. The full factorial is run under
both generators: mechanism $\times$ het $\times$ info $\times$ concentration $\times$ $n$, five
seeds, everything else at the published protocol including the tuned baselines and nested-CV
$\kappa$ selection. The reported quantity is the same one the paper reports, the safe-adaptive
estimator's mean gain over the tuned indicator baseline.

## What is already seen, and disclosed

A four-cell quick grid, two seeds, run before this file. At MAR, het $= 1.5$, info $= 1.5$,
$n = 2000$: the standard generator gives $+0.2962$ (10 of 10 folds, $p = 0.002$) and the control
gives $+0.0000$ (1 of 10 folds, $p = 1.0$), at an identical realised coefficient spread of $1.132$.
The thresholds below are set with those numbers in view.

## Predictions

C1. Under the standard generator the mean gain rises with het, and at het $= 1.5$ it exceeds $+0.05$.
C2. Under the control the mean gain is within $\pm 0.01$ of zero at every level of het.
C3. At het $= 1.5$ the difference between the two generators exceeds $+0.10$.
C4. Build check: the realised coefficient spread agrees between the two generators to within $1\%$
    at matched het, so the control differs in the outcome draw and in nothing else.
C5. Under the control the gain does not rise with het, so what the standard generator rewards is the
    predictive divergence and not the coefficient divergence.

## Withdrawal

(a) C2 or C5 fails: the family gains something under the control too, which would mean coefficient
    heterogeneity alone is exploitable and the paper's explanation is wrong or incomplete. The
    explanation section would have to be rewritten, and the real-data null would need another
    account.
(b) C4 fails: the two generators differ in more than the outcome draw and the comparison is void.
(c) C1 fails: the standard generator does not reproduce the published gains, so the factorial is not
    the one the paper reports and nothing can be concluded.

## Outcome (2026-09-08 09:3x; 108 configurations per generator, 5 seeds; `experiments/score_simcontrol.py`)

**C2, C4 and C5 held --- the three that bear on the control. C1 and C3 failed, on thresholds set from
an unrepresentative pilot.**

Safe-adaptive gain over the tuned indicator baseline, by slope heterogeneity:

| het | standard generator | control | realised coefficient spread |
|---|---|---|---|
| $0.0$ | $+0.0011$ | $+0.0011$ | $0.0000$ in both |
| $0.5$ | $+0.0059$ | $+0.0011$ | $0.4802$ in both |
| $1.5$ | $+0.0429$ | $+0.0011$ | $1.4406$ in both |

By mechanism at het $= 1.5$: MAR $+0.0657$ against $+0.0001$; MNAR $+0.0408$ against $+0.0023$;
MCAR $+0.0221$ against $+0.0010$.

C4 held exactly: the realised coefficient spread is **identical** between the generators, to zero
relative difference, so the control differs in the outcome draw and in nothing else. C2 held: the
control's gain is $+0.0011$ at every level of het, the same number three times, because the outcome
does not depend on het at all. C5 follows.

**The demonstration the paper lacked is now in hand.** At identical coefficient divergence, drawing
the outcome from the diverging coefficients produces a gain that grows with that divergence, and
drawing it from a shared vector produces nothing.

### Why C1 and C3 failed, and why that does not void the run

C1 required the standard generator's gain to exceed $+0.05$ at het $= 1.5$ and it reached $+0.0429$;
C3 required a between-generator difference above $+0.10$ and it was $+0.0418$. Both thresholds came
from a four-cell quick grid at MAR, info $= 1.5$, $n = 2000$, concentration $0.9$ --- a single
favourable corner that gave $+0.2962$. The full factorial averages over 108 cells including MCAR,
$n = 1000$, and concentrations that produce 300 patterns. **This is the fourth time in two days that
a small pilot has overstated an effect.**

Withdrawal condition (c) reads: "C1 fails: the standard generator does not reproduce the published
gains, so the factorial is not the one the paper reports and nothing can be concluded." Its premise
is false, and the check is direct. Against the paper's published 108-cell synthetic suite:

| | published (10 seeds) | this run (5 seeds) |
|---|---|---|
| configurations | 108 | 108 |
| largest gain | $+0.2496$ | $+0.2495$ |
| significant wins | 40 | 39 |
| mean gain | $+0.0201$ | $+0.0166$ |

The standard arm reproduces the published factorial. The mean is lower because this run uses five
seeds against the paper's ten. So C1 and C3 failed as thresholds on a quantity the paper already
publishes, not because the factorial is the wrong one, and the predictions that bear on the control
--- C2, C4, C5 --- all held.

We report C1 and C3 as failed. The claim the paper will make rests on C2 and C5.

### An incidental finding worth reporting

The control produces **30 significant wins of 108** at a mean gain of $+0.0011$ and a maximum of
$+0.0210$. Significance without magnitude, from paired folds with low variance, in a setting
constructed to have nothing to find. That belongs beside the paper's own real-data result, where the
argument runs the other way and no dataset reaches $p < 0.05$.
