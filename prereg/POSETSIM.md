# POSETSIM: numerical kill test for the poset-Lipschitz rate conjecture (pre-registered 2026-09-06 15:05)

From `papers/POSET-SHRINKAGE-THEORY-PRIOR-ART.md` §4 and §6. The conjecture: when pattern-wise coefficients are close
along the containment poset (child within tau of parent), ancestor shrinkage attains a rate whose gain over Ayme et
al.'s thresholded pattern-by-pattern estimator is a tail functional of the pattern law (mass on patterns with n_e < d).

## Design (`experiments/probe_posetsim.py`)
GPMM, d = 8, X ~ N(0, I), y = x_obs . beta_e + N(0, 1); beta walks down the lattice with step tau; Zipf(alpha) pattern
law over the 255 nonempty patterns. Cells: n in {2000, 20000} x alpha in {0.8, 1.2, 2.0} x tau in {0, 0.05, 0.2, 1};
5 seeds; test n = 20,000. Estimators: pbp, ayme, shrink_kappa (kappa in {1, 10, 100, 1000}), shrink_cv, shrink_oracle,
global ridge, tree on (zero-filled values, indicators). Excess MSE = test MSE - 1. Per cell: mean over seeds.
gain = excess(ayme) - excess(shrink_cv). tail_mass = sum of pattern mass with n p_e < d (recorded per cell).

## Predictions
P1. At tau = 0, gain > 0 in all 6 (n, alpha) cells and Spearman(gain, tail_mass) > 0 across them.
P2. For every (n, alpha), gain is non-increasing in tau (0 -> 0.05 -> 0.2 -> 1, ties allowed), and at tau = 1
    excess(shrink_cv) <= 1.1 x excess(ayme) (shrinkage never harms).
P3. The pooled tree does not match: at tau <= 0.05, excess(tree) >= 1.5 x excess(shrink_cv) in >= 5 of 6 cells.
P4. CV finds kappa: excess(shrink_cv) <= 1.2 x excess(shrink_oracle) in >= 20 of 24 cells.

## Withdrawal
(a) P1 fails -> the effective-sample-size mechanism is absent; the theorem is dead.
(b) P2 fails -> poset distance is not the operative structure; dead.
(c) P3 fails -> the theorem, even if true, describes nothing a practitioner should do (consistent with the 17-dataset
    finding); dropped as a project.
(d) P4 fails -> the estimator is not practical without an oracle; the theory may stand but no method paper.

## Outcome (2026-09-06 15:25; scorer `experiments/score_round6.py`)

P1 HOLDS (gain > 0 in 6/6 cells at tau = 0; Spearman(gain, tail mass) = +0.94), P3 HOLDS (6/6), P4 HOLDS (24/24).
P2 FAILS: the gain over Ayme's estimator is non-increasing in tau in only 1 of 6 cells and is LARGEST at tau = 1 in
every n = 2,000 cell (2.26 -> 4.72 at alpha 0.8). Withdrawal (b) fires: poset distance is not the operative structure.
The gain is generic shrinkage of tiny per-pattern fits toward anything sensible, which grows as the per-pattern
truth gets noisier, exactly the "Ayme's rate with n_e -> N_e" reduction the prior-art note warned of. Also: a global
ridge beats every poset estimator at tau <= 0.05 (coefficients effectively shared), so the poset only matters in a
window of intermediate tau. The theorem project is dead by its own rule.
Disclosure: one-seed smoke of the n = 2000, alpha = 1.2 job on dugong after the freeze.

Scorer output, verbatim:

```
=== POSETSIM (1200 rows, cells 6/6) ===
P1 tau=0 gain > 0 in 6/6 cells; Spearman(gain, tail_mass) = +0.943 (> 0): HOLDS
P2 gain non-increasing in tau in 1/6 cells, no harm at tau=1 in 6/6: FAILS
P3 tree >= 1.5 x shrink_cv at tau <= 0.05 in 6/6 cells (needs >= 5): HOLDS
P4 shrink_cv <= 1.2 x oracle in 24/24 (needs >= 20): HOLDS
                  global    pbp   ayme  shrink_cv  shrink_oracle   tree   gain   tail
n     alpha tau                                                                      
2000  0.8   0.00   0.006  4.429  2.269      0.014          0.014  0.176  2.255  0.388
            0.05   0.028  4.432  2.283      0.034          0.034  0.194  2.249  0.388
            0.20   0.346  4.486  2.444      0.202          0.196  0.471  2.241  0.388
            1.00   8.461  5.894  6.347      1.629          1.629  7.323  4.717  0.388
      1.2   0.00   0.007  2.572  2.393      0.043          0.041  0.164  2.349  0.218
            0.05   0.024  2.574  2.402      0.052          0.052  0.175  2.350  0.218
            0.20   0.278  2.613  2.492      0.156          0.156  0.367  2.336  0.218
            1.00   6.761  3.688  4.553      1.121          1.121  5.004  3.432  0.218
      2.0   0.00   0.007  0.277  0.268      0.021          0.021  0.142  0.247  0.046
            0.05   0.014  0.279  0.269      0.024          0.024  0.147  0.245  0.046
            0.20   0.132  0.292  0.285      0.053          0.052  0.216  0.232  0.046
            1.00   3.259  0.605  0.714      0.334          0.334  1.897  0.380  0.046
20000 0.8   0.00   0.002  0.078  0.078      0.003          0.003  0.057  0.075  0.000
            0.05   0.023  0.078  0.078      0.016          0.016  0.077  0.062  0.000
            0.20   0.336  0.078  0.078      0.049          0.049  0.328  0.029  0.000
            1.00   8.302  0.078  0.078      0.073          0.073  6.439  0.005  0.000
      1.2   0.00   0.002  0.376  0.195      0.003          0.003  0.058  0.192  0.014
            0.05   0.019  0.376  0.195      0.012          0.011  0.070  0.184  0.014
            0.20   0.270  0.375  0.200      0.039          0.039  0.234  0.160  0.014
            1.00   6.665  0.386  0.345      0.106          0.106  4.185  0.238  0.014
      2.0   0.00   0.002  0.210  0.092      0.005          0.005  0.051  0.087  0.013
            0.05   0.010  0.211  0.092      0.007          0.007  0.054  0.085  0.013
            0.20   0.131  0.215  0.096      0.015          0.015  0.105  0.081  0.013
            1.00   3.197  0.294  0.222      0.073          0.073  1.310  0.150  0.013
```
