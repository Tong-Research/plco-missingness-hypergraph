# A4b — rescaled residual mask, and a null that works — pre-registered 2026-08-27 10:47, BEFORE the run

Result 141 left two things open. A4b closes both in one run.

## 1. The null

A4's null rebuilt the feature matrix from the permuted mask and filled newly-observed cells from
column means, changing the **values** as well as the mask. Its own output convicted it: the real
arm beat the permuted arm by $+0.0207$ on lung **for `mean_impute`**, a method that never sees the
mask.

The replacement permutes only the indicator block inside the design; the values are built once
from the real `X` and never touched. `masked_design.selftest()` asserts four things, and each was
confirmed to fail under a deliberate mutation before being trusted:

| assertion | mutation that breaks it |
|---|---|
| `kind="none"` reproduces `mean_impute_lr` bit-for-bit | drift the estimator to `C=0.5` |
| `kind="raw"` reproduces `mean_indicator_lr` bit-for-bit | drop the mask block |
| permuting the mask leaves the mask-blind arm **identical** | reintroduce the Result 141 bug |
| permuting the mask **does** move the raw-mask arm | make `perm_seed` a no-op |

The third is the one A4's null failed.

## 2. The rescaling hypothesis

Result 141 offered a mechanism for why residualising *hurt*: the estimator carries an L2 penalty,
the raw mask is binary with unit scale, and the residual is smaller because the fitted part was
subtracted. Under a fixed penalty a smaller column buys less. A4b adds
`scaled_residual_indicator`, which puts each residual column back on its raw mask column's own
standard deviation, using **train statistics only**.

## Predictions

1. **`scaled_residual_indicator` beats `residual_indicator`** by $\ge 0.002$ on both dev cohorts.
   This is the direct test of the L2 mechanism.
2. **`scaled_residual_indicator` does NOT beat `mean_impute`** by the floor. Fixing a scaling
   artefact should recover what the artefact cost and no more; the mask still carries nothing that
   the values do not.
3. **Under the corrected null, `mean_impute` real minus permuted is exactly $0.000000$** on every
   cell. Not small — zero. This is the instrument check, and it is the reason to believe anything
   else in the table.
4. **`mean_indicator` real does not beat `mean_indicator` permuted** by the floor. The raw mask's
   association with the outcome is worth less than the degrees of freedom it costs, so destroying
   that association should cost nothing.

## Withdrawal conditions

- **(a) If prediction 3 fails** — any non-zero difference at all — the null is still touching the
  values. Stop; report nothing from this run; find it.
- **(b) If prediction 1 fails**, the L2 mechanism offered in Result 141 is wrong, and A4 is
  recorded as refuted with its cause **unidentified** rather than explained. No third rescue
  attempt: two failed mechanisms is the point at which the idea is closed.
- **(c) If prediction 2 fails** — `scaled_residual_indicator` beats `mean_impute` by $\ge 0.002$
  paired on both dev cohorts and beats its own corrected null — then the mask carries
  non-recoverable signal and Paper 1's discussion must be rewritten before submission. This is the
  same condition A4 carried, and it is the only outcome here that would change the paper.

## Scope

Development cohorts colorectal and lung only; ovarian and prostate refused in code. 5 seeds x 5
folds, 40,000-record subsample, baseline features. Levels are not comparable to the paper's main
table (different seed count and subsample draw) and are not reported as such; all contrasts are
paired within `(seed, fold)`.
