# Paper 3's MIMIC-IV test, replicated under a committed script — pre-registration

**Written 2026-09-03 10:05, before any run. Frozen on commit.**

## Why
Paper 3 (`sections-diagnostic.tex`, `sections-simulation.tex`) reports a MIMIC-IV test of the pre-fit
diagnostic and of the shrinkage family: $H_{\mathrm{exc}} = +0.420$, tuned imputation 0.2990, tuned indicator
0.3323, safe-adaptive 0.3323, oracle 0.3323, $\Delta$ vs the indicator $+0.0000$ in 0 of 10 folds. Those
numbers were produced on 2026-08-08 by `run_real_suite.evaluate` on an extract (`mimic_iv.csv`: 28 labs,
40,000 records, prevalence 2.7 %) that was never versioned. This replicates the test on the committed
matrix `mimic4_sites.npz` (42 first-24 h labs, first ICU stay, in-hospital mortality, prevalence 11 %),
subsampled to 40,000 with seed 0, with the same evaluator and the same diagnostics code.

## Runs
- `run_real_suite.py --only mimic4 --seeds 2 --out results/p3mimic_suite.csv` (10 folds, as before)
- `oracle_ceiling_b.py --datasets mimic4 --seeds 3 --B 50 --out results/p3mimic_ceiling.csv`

## Predictions (Paper 3's claims, restated for this matrix)
1. $\Delta$ (safe-adaptive − tuned indicator) lies within $\pm 0.002$ and is not significant: a tie.
2. safe-oracle equals tuned indicator to within $0.002$: the oracle $\kappa$ is the pooled model.
3. $H_{\mathrm{exc}} > 0$ (measured $+0.104 \pm 0.074$ on this subsample on 2026-09-02; the sign is the claim,
   the magnitude will differ from the 28-lab extract's $+0.420$ and the paper must say so).
4. Ceiling: real $\le$ permuted mean (excess $\le 0$), as on the eleven datasets.

## Withdrawal / what changes the paper
- If 1 fails with $\Delta \ge +0.002$ and $p < 0.05$: Paper 3's "decisive case" is not decisive on this
  cohort; the section is rewritten to report both extracts honestly, and Paper 1's M1 becomes the primary
  MIMIC evidence.
- If 3 fails ($H_{\mathrm{exc}} \le 0$): the diagnostic did not flag this cohort; the "flagged in advance"
  sentence is withdrawn for this matrix.
- Whatever lands, the prose states the extract (labs, n, prevalence) beside every MIMIC-IV number.

---
**Outcome, 2026-09-03 17:05 (appended; `score_p3mimic.py` on `results/p3mimic_suite.csv` and `results/p3mimic_ceiling.csv`).**
n = 40,000, d = 42; ι +0.227, H +1.254, H_exc +0.019 (single permutation seed; five seeds on the same subsample:
+0.104 ± 0.074), c30 0.873. tuned_impute 0.3585, tuned_indicator 0.3851, safe_adaptive 0.3851, safe_oracle
0.3851; Δ vs indicator +0.0000, p = 1, 0/10 folds. Ceiling real +0.0000, permuted mean +0.0001 [+0.0000, +0.0006],
excess −0.0001, p = 0.98. All four predictions HOLD. No withdrawal. The prose states both extracts.
