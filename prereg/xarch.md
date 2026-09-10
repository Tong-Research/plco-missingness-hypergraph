# Cross-architecture reproducibility — pre-registered 2026-09-02 10:47, BEFORE any run

## Why

The homelab gained two x86_64 Linux machines. Before any experiment is split across them, the
question is whether a number computed on Linux is comparable to one computed on macOS at the
resolution this project reports. The article states a measured reproducibility bound of
$4.5\times10^{-5}$ AUPRC (Result 130) and a reporting floor of $0.002$. If the cross-architecture
gap exceeds the bound, the bound is wrong; if it approaches the floor, the cluster cannot be mixed
within a cohort at all.

## Design

`run_idea.py --idea A4b --cohort colorectal` on **spinner** (arm64 macOS, Accelerate) and on
**dugong** (x86_64 Linux, OpenBLAS). It writes 200 per-cell AUPRC values at fixed seeds and folds,
takes about five minutes, and every arm is deterministic given the data.

Dugong was pinned to spinner's exact stack — python 3.12.13, numpy 2.5.1, pandas 3.0.5,
scikit-learn 1.9.0, scipy 1.18.0 — so **architecture and BLAS are the only uncontrolled
differences**. Pilot is included as a third point but is a weaker comparison: it runs python
3.12.14 and pandas 3.0.3, so a pilot-versus-anything gap confounds versions with hardware. The
measurement of record is **spinner versus dugong**.

## Predictions

1. **The paired median difference is $0.000000$** on every arm. Architecture changes rounding, not
   expectation; a non-zero median would mean one platform is systematically biased, which would be
   a far larger finding than a tolerance.
2. **The maximum single-cell $|{\Delta}|$ exceeds the arm64-to-arm64 gap** of $3.7\times10^{-6}$
   measured yesterday between pilot and spinner. Different BLAS should be worse than same BLAS.
3. **The maximum single-cell $|{\Delta}|$ stays below the $0.002$ floor.** Anything else means a
   single cell can move a reported effect by more than the effect itself.

## Decision rule, fixed in advance

| max single-cell $|{\Delta}|$ | verdict |
|---|---|
| $\le 4.5\times10^{-5}$ | the existing bound already covers cross-architecture; mix freely |
| $> 4.5\times10^{-5}$ but $< 0.002$ | bound must be restated to the measured value; whole jobs pinned to one machine, never a cohort split |
| $\ge 0.002$ | Linux machines cannot contribute numbers to this article; use them for orthogonal work only |

## Withdrawal conditions

- **(a) If prediction 1 fails** — any arm shows a non-zero paired median with $p < 0.05$ — stop.
  That is a systematic platform difference, not tolerance, and nothing else here is interpretable
  until it is explained.
- **(b) If the two platforms disagree on which arm wins any comparison**, the gap is scientifically
  material regardless of its size, and the mixing rule must be "never" rather than "not within a
  cohort".
- **(c) If dugong's run fails or produces a different row count**, this is a provisioning failure
  and not a measurement; fix and re-run rather than reporting a gap.

## Scope

One idea, one cohort, 200 cells. It bounds the gap for this estimator and design; it does not
bound it for tree baselines or for `mask_interaction`, whose sparse path may behave differently.
Stated as a limitation rather than generalised.
