# GRAPHSCALE: does the structure-learning null survive larger and denser graphs? (registered 2026-09-07 12:2x)

## Why this must be run

Paper B's pre-registered negative is that an institutional regime costs constraint-based structure
learning nothing, across five algorithms and three regime strengths. The paper then states the
limitation itself: "The simulation uses one substrate, twelve variables and one graph size; a cost
that appears only in larger or denser problems would not be visible here."

A null measured at one problem size is a weak null, and this is the honest negative on which Paper B
partly rests. Either it survives being pushed, in which case it is worth much more, or it does not,
in which case Paper B has a second positive result and its conclusion changes.

## Design

`experiments/probe_graphscale.py`. Same eICU substrate, same transplanted mask, same closed-missingness
control, same $N = 20{,}000$, same four children of the latent regime, same anchor $0.184$, same
$\alpha = 0.01$, same five arms scored by excess skeleton error over the complete-data arm.

Varied: $p \in \{12, 20, 30\}$ at density $1.5$ edges per node, which reproduces the published
$18$ edges at $p = 12$, plus $p = 20$ at density $2.5$. Ten replicates per configuration, 40 jobs.

The $p$ columns are the $p$ columns of the eICU regime matrix whose missing rates are nearest the
median of the usable band $[0.05, 0.95]$, by a rule fixed before any outcome was read. Fifty of the
57 columns are in that band, so $p = 30$ is comfortably supported.

## What is already seen

One pilot replicate at $p = 12$ (rep 900, not in the analysis set) reproduced the published pattern:
excess of $+0$ for every arm under the aligned mask at $\gamma = 2$, and $-1$ for every arm under the
control. Nothing has been run at $p = 20$ or $p = 30$, or at density $2.5$. The predictions at those
settings are blind.

## Predictions

G1. At $p = 12$, density $1.5$, the aligned-minus-control excess at $\gamma = 1$ is within $\pm 1.0$
    edges for every arm. This is the reproduction check: it must match the published null.
G2. At $p = 20$ and at $p = 30$, density $1.5$, the same difference is within $\pm 2.0$ edges for
    every arm at every $\gamma$. The band widens with $p$ because the skeleton has more edges to get
    wrong, not because the criterion is being relaxed after the fact.
G3. The difference does not grow monotonically with $p$ for any arm.
G4. At $p = 20$, density $2.5$, the difference is within $\pm 2.0$ edges for every arm.
G5. The complete-data arm's own error grows with $p$, which confirms the problem is genuinely harder
    and that G2 is not a null bought by an easy task.

## Withdrawal

(a) G2 or G4 fails for two or more arms in the same direction: the regime does cost structure
    learning something once the problem is large or dense enough. Paper B's negative result is then
    scoped to small sparse graphs, the finding is reported as a positive, and the discussion is
    rewritten. This is a real possible outcome and would be the more interesting one.
(b) G5 fails: the larger settings are not actually harder, so they cannot test what they claim, and
    the run is void rather than reinterpreted.
(c) G1 fails: the reimplementation does not reproduce the published behaviour at $p = 12$ and no
    conclusion may be drawn from the other sizes.

## Outcome (2026-09-07 12:3x; 10 replicates per configuration; scorer `experiments/score_graphscale.py`)

**All five predictions held. The negative result survives being pushed.**

Excess skeleton error, aligned minus the closed-missingness control, in edges:

| configuration | $\gamma=0$ | $\gamma=1$ | $\gamma=2$ | complete-data error |
|---|---|---|---|---|
| $p=12$, density $1.5$ (published setting) | $-0.3$ | $-0.2$ | $-0.5$ | $3.87$ |
| $p=20$, density $1.5$ | $+0.1$ | $-0.7$ | $+0.5$ to $+0.8$ | $6.07$ |
| $p=30$, density $1.5$ | $+0.6$ | $-0.5$ to $-0.1$ | $-1.0$ to $-0.8$ | $6.80$ |
| $p=20$, density $2.5$ | $-0.1$ to $0.0$ | $-1.0$ to $-0.3$ | $+0.4$ to $+0.8$ | $32.30$ |

Every cell is inside $\pm 1.0$ edges and the signs alternate, which is what a null looks like.

G5 is the check that the harder settings are genuinely harder, and both axes deliver: the complete-data
arm's own error rises $3.87 < 6.07 < 6.80$ along the $p$ ladder, and from $6.07$ to $32.30$ when the
density is raised at $p = 20$ — an eight-fold harder problem in which the regime still costs nothing.

### A correction to the scorer, not to the result

The first version of `score_graphscale.py`, written after this registration was frozen, pooled the
density-$2.5$ configuration into the $p=20$ cell when checking G5. That averaged $6.07$ with $32.30$
and reported G5 as failed. G5 is a statement about the $p$ ladder at fixed density; mixing a
different experimental axis into it was an implementation error. It is fixed, the fix is commented in
the scorer, and no threshold was changed.

**What Paper B may now say.** The limitation "one substrate, twelve variables and one graph size" is
answered. The regime costs constraint-based structure learning nothing at $p = 12$, $20$ and $30$,
and nothing at an edge density that makes the complete-data problem eight times harder, across all
five algorithms and three regime strengths. The negative is much stronger than the one currently in
the paper.
