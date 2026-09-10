# ZERODEL: does the ICLR 2024 dropout correction survive a latent regime? (registered 2026-09-07 23:4x)

## Why this is the right comparison

Our Related Work names Dai et al. (ICLR 2024 oral, arXiv:2403.15500) as the closest published work:
they state a no-indicator-edge assumption, write that it is desirable to verify it empirically, and
relax it. Their contribution is a theorem, stated in one sentence on their own repository:

> "conditional independence (CI) relations in the data with dropouts, after deleting the samples with
> zero values for conditioned variables, are identical to the CI relations in the original data."

Their assumption (A3) is that a variable's dropout is directly affected only by that variable's own
value. Our regime violates it: the mask is driven by a latent institution, which is not a variable
the model sees. So the theorem's premise fails on our data and its conclusion can be checked.

This is a test of a published theorem's own conclusion, using the authors' own code, unmodified.

## Design

`experiments/probe_zerodel.py` on the PLASMODE export, $\gamma \in \{0,1,2\}$ crossed with the
aligned mask and the closed-missingness control. Missing values are encoded as $0$, which is their
dropout convention; our variables are Gaussian so an exact zero has measure zero and "is zero"
coincides with "is missing".

For 300 random triples $(X, Y, \mathbf{Z})$ with $|\mathbf{Z}| \le 3$ we compare the CI verdict at
$\alpha = 0.01$ on the complete data against the verdict their deletion rule returns on the masked
data, and report the agreement rate. Two rules, both theirs:

* **cond** --- delete rows where any conditioning variable is zero. This is their default and the
  rule their theorem licenses.
* **all** --- delete rows where any involved variable is zero. This is the alternative their own
  docstring offers, noting it is "still correct ... though it may be less powerful".

The complete data are identical between the aligned and control conditions at a given $\gamma$; only
the mask differs. The ground-truth verdicts are therefore the same in both, and any difference in
agreement is caused by the deletion alone. Twenty replicates.

## What is already seen, and disclosed

One replicate at 100 triples, run before this file:

| $\gamma$ | cond, aligned | cond, control | all, aligned | all, control |
|---|---|---|---|---|
| 0 | 0.900 | 0.920 | 0.930 | 0.950 |
| 1 | 0.880 | 0.890 | 0.910 | 0.930 |
| 2 | 0.830 | 0.900 | 0.880 | 0.920 |

At 100 triples the standard error of an agreement rate is about $0.03$, so only the $\gamma = 2$
aligned cell is more than two standard errors from its control. The thresholds below are set with
that in view and the full run uses 300 triples and twenty replicates.

## Predictions

Z1. For their rule, the aligned-minus-control agreement gap is at least $0.03$ at $\gamma = 2$.
Z2. That gap is larger at $\gamma = 2$ than at $\gamma = 0$.
Z3. At $\gamma = 0$ the gap is within $\pm 0.02$ of zero. Null control: with no regime there is
    nothing for the mask to be aligned with.
Z4. Deleting on all involved variables agrees with the complete data at least as often as their
    conditioning-only rule, in every cell. Their docstring predicts the opposite ordering on power
    grounds, so this is the prediction most likely to fail.

## Withdrawal

(a) Z1 or Z2 fails: the regime does not measurably degrade their rule, the theorem survives our
    violation of its premise in practice, and we report that. It would be a point in their favour
    and a limit on how far our result generalises.
(b) Z3 fails: alignment matters without a regime, so the two conditions differ in something other
    than the regime and the comparison is void.
(c) Z4 fails: their conditioning-only rule is the better of the two here, which would mean the
    power argument dominates and our reading of why it degrades is wrong.

Registered once. Whatever twenty replicates return is what we report, and no result from this run
will be presented as a defect in their method without stating that its premise does not hold here.

## Outcome (2026-09-08 00:0x; 20 replicates x 300 triples; scorer `experiments/score_zerodel.py`)

**Z1 and Z2 failed. Z3 and Z4 held. Their theorem's conclusion survives our violation of its
premise, and we report that as a point in their favour.**

Agreement with the complete-data CI verdict:

| $\gamma$ | their rule, aligned | their rule, control | delete-on-all, aligned | delete-on-all, control |
|---|---|---|---|---|
| 0 | $0.9343$ | $0.9373$ | $0.9655$ | $0.9667$ |
| 1 | $0.9333$ | $0.9325$ | $0.9640$ | $0.9655$ |
| 2 | $0.9137$ | $0.9167$ | $0.9443$ | $0.9427$ |

Control minus aligned, for their rule: $+0.0030 \pm 0.0025$ at $\gamma = 0$, $-0.0008 \pm 0.0043$ at
$\gamma = 1$, $+0.0030 \pm 0.0041$ at $\gamma = 2$. Every one is inside its own standard error. Z1
asked for a gap of at least $0.03$ at $\gamma = 2$ and the measured gap is a tenth of that.

Both rules do lose accuracy as the regime strengthens, from $0.934$ to $0.914$ and from $0.966$ to
$0.944$, but they lose it **equally under the aligned mask and under the control**. That degradation
is the problem becoming harder, not the mask becoming informative.

The pilot in this file showed a gap of $0.070$ at $\gamma = 2$ from one replicate of 100 triples,
against a standard error of about $0.03$. Twenty replicates of 300 put the true value at $0.003$. The
pilot was noise, and this is the third time today a small pilot has pointed the wrong way.

**Z4 held**, and it is worth stating: deleting on all involved variables agrees with the complete
data about three points more often than their conditioning-only rule, in every one of the six cells.
Their docstring predicts the reverse on power grounds. At a $47\%$ missing rate the accuracy gain
from conditioning on more complete rows outweighs the sample-size loss.

### What this means for the paper, and it is a limit rather than a win

Dai et al.'s deletion rule is **robust to the configuration we report**. Its premise (A3) does not
hold on our data and its conclusion holds anyway.

That is consistent with our own MISCOST result rather than in tension with it. There we found the
correlation matrix a constraint-based algorithm consumes is undistorted to within $0.002$; here we
find the CI verdicts read off it are undistorted too. Both say the same thing, and it sharpens the
claim the paper should make: **the regime corrupts what a method reports about the mechanism, not the
statistical machinery the method runs on.** MVPC's detection step is fooled; the deletion-based
independence testing underneath it is not.

The paper must therefore not say that the regime breaks causal discovery. It says that a correct
diagnostic identifies the wrong mechanism, and this run is evidence for exactly that boundary.
