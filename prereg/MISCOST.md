# MISCOST: is the quantity a discovery algorithm consumes actually distorted? (registered 2026-09-07 14:3x)

## Why this must be run

The merged paper reports that an institutional regime makes MVPC's detection step name the observed
values as parents of the missingness indicators, when the dependence is induced by an unobserved
common cause. It also reports that the same regime costs constraint-based structure learning nothing.
It is currently explicit that it does not measure any downstream cost, and a referee will ask why the
two results do not contradict each other.

This resolves that. A constraint-based algorithm reads partial correlations off the correlation
matrix, so a bias there is a bias in every independence test it runs. If the matrix is undistorted,
the structure-learning null has a mechanism and the paper's two halves are consistent.

## Design

`experiments/probe_miscost.py`, on the PLASMODE substrate, at $\gamma \in \{0, 1, 2\}$ against the
closed-missingness control. Estimand: the 66 off-diagonal entries of the correlation matrix, with the
complete-data correlation on the same rows as truth. Four estimators: pairwise-complete correlation
(what test-wise deletion uses), and the correlation after imputation from the observed values alone,
within each mask-estimated latent class, and within each true hospital.

The scored quantity is the **per-pair signed error averaged over replicates**. Sampling noise cancels
in that average and a systematic distortion does not, which is the only way this design can separate
"no bias" from "a bias below the noise floor of one sample". Forty replicates.

## Power, stated before the run

Each pair has a median of $6{,}463$ rows observed on both variables, so one replicate resolves a
correlation to about $0.012$. Averaged over forty replicates the resolvable bias is about $0.0020$.
**Any bias smaller than that is invisible to this design and will be reported as such, not as zero.**

## What is already seen, and disclosed

One pilot replicate, on RMSE rather than signed error. Pairwise-complete correlation gave $0.0088$ to
$0.0119$ across all six cells, with no pattern in $\gamma$ or alignment, and the highest value in a
*control* cell. That is at or below the single-replicate sampling floor of $0.0124$, so the pilot is
consistent with no bias, and the predictions below expect a null.

An earlier design, scoring twelve stacked leave-one-out regressions, was written and discarded: with
a $47\%$ missing rate almost no row is complete on twelve columns, so its available-case arm fell
through its own guard and returned zeros, which scored best because the true coefficients are mostly
zero. That design is recorded in the probe's docstring as a warning and is not used.

## Predictions

C1. For pairwise-complete correlation the mean signed error, averaged over pairs and replicates, is
    within $\pm 0.005$ of zero at every $\gamma$ under the aligned mask.
C2. The aligned-minus-control difference in that mean signed error is within $\pm 0.005$ at every
    $\gamma$.
C3. The root-mean-square of the per-pair mean signed errors does not grow with $\gamma$ under the
    aligned mask: its value at $\gamma = 2$ is at most twice its value at $\gamma = 0$.
C4. No estimator's aligned-minus-control difference exceeds $\pm 0.01$ at any $\gamma$.

## Withdrawal

(a) C1 or C3 fails: the regime **does** distort the correlation matrix. That would be a positive
    result and a more interesting one. The structure-learning null would then need a different
    explanation, since the quantity feeding it is biased, and the paper would have to reconcile them.
(b) The pilot's pattern reverses under signed-error scoring: the design is measuring something other
    than what it claims and the run is void.

If C1 to C4 hold, the paper gains the mechanism for its own negative result: the regime corrupts the
diagnosis without corrupting the sufficient statistic, so the graph survives and the reported
mechanism does not. If they fail, the paper gains a cost it currently says it cannot demonstrate.
Either outcome is reported. This comparison is registered once.

## Outcome (2026-09-07 14:5x; 40 replicates, 63,360 pair-observations; scorer `experiments/score_miscost.py`)

**All four predictions held. The null is real and it is powered.**

Pairwise-complete correlation, which is what test-wise deletion uses, scored as the per-pair signed
error averaged over the forty replicates:

| $\gamma$ | mean signed error, aligned | closed | RMS of per-pair means, aligned | closed |
|---|---|---|---|---|
| 0 | $+0.00040$ | $+0.00009$ | $0.00156$ | $0.00159$ |
| 1 | $+0.00029$ | $+0.00011$ | $0.00158$ | $0.00179$ |
| 2 | $+0.00012$ | $-0.00005$ | $0.00194$ | $0.00169$ |

The resolvable bias on forty replicates is $0.0020$. Every RMS above is at or below it, the aligned
and control columns are indistinguishable, and nothing grows with the regime. The mean signed error
never exceeds $0.0004$ against a registered tolerance of $0.005$.

The imputation arms are all worse than pairwise deletion and none shows an alignment effect either:
imputing from the observed values alone carries a mean signed error of about $-0.0019$ at every
setting, and imputing within a class or within a hospital adds noise ($0.02$ to $0.03$ RMS) without
removing any bias, because there is no bias to remove.

**This is the mechanism for the paper's own negative result.** A constraint-based algorithm reads
partial correlations off the correlation matrix. That matrix is undistorted here, to within $0.002$
in correlation units, which is the resolution of this design. So the regime corrupts the diagnosis
without corrupting the sufficient statistic the diagnosis sits on top of, and the graph survives
while the reported mechanism does not. The two results the paper reports are not in tension; one
explains the other.

**What may not be said.** A bias smaller than $0.002$ would be invisible here, and this is one
substrate, one estimand and one regime strength scale. The claim is that the distortion is below
what forty replicates of twenty thousand rows can resolve, not that it is exactly zero.
