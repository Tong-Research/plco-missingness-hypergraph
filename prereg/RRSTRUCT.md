# RRSTRUCT: is the indicator-indicator dependence a low-dimensional latent regime or direct edges? (pre-registered 2026-09-06 18:30)

Follows Result 209 and `papers/LEAD-CAUSAL-DISCOVERY-MISSING.md`. Three published causal-discovery methods for
missing data assume no edges among missingness indicators (Strobl, Visweswaran & Spirtes 2018 Assumption 1;
Tu et al. AISTATS 2019, whose proofs use "missingness indicators are the leaf nodes"; Liu & Constantinou 2022
Assumption 1). Result 209 says indicators predict each other at AUROC 0.81-1.00. This experiment decides WHICH
published assumption the fact violates: direct R->R edges, or causal sufficiency over R (a latent regime that is a
common parent of every indicator, which also breaks MissDAG's ignorability and MissNODAG's no-unmeasured-confounder
assumption). **Both outcomes contradict a published assumption; the experiment selects the claim, it does not decide
whether there is one.** The genuine kill is registered at the end.

## Design (`experiments/probe_rrstruct.py`)
17 registered datasets. Panels = Jaccard >= 0.9 co-missing clusters, defined on the DEV half; a panel's presence is
its representative column's indicator (representative = the column whose missing rate is closest to the cluster
median). All models are FIT on dev (cap 60,000) and evaluated on HOLDOUT (cap 60,000, seed 0). For each panel with
base rate in [0.01, 0.99] on both halves, AUROC for predicting that panel MISSING from: the always-observed columns'
values (tree); the other panels (tree); the other panels (L1 logistic, i.e. Ising neighbourhood selection); the other
panels through a K-class Bernoulli-mixture posterior, K in {1,2,5,10,20,50,100} fitted by EM on dev (seed 0, 200
iterations, Laplace 1e-3); and values + other panels (tree). A Bernoulli mixture is exactly the model in which the
indicators are conditionally independent given a latent class, i.e. "a latent regime and no direct edges". On eICU and
MIMIC-IV the mixture's class assignment is compared with the hospital/unit id (adjusted mutual information, and
class purity relative to the majority-hospital baseline).

## Predictions
P1 (regime versus edges). Averaged over panels, the best mixture with K <= 20 reaches >= 0.95 x the unrestricted
   tree AUROC on >= 12 of 17 datasets.
P2 (the regime is institutional). On eICU, the best K <= 100 mixture's class purity for hospital is >= 3x the
   majority baseline and adjusted mutual information with hospital is >= 0.15; on MIMIC-IV, purity >= 1.5x.
P3 (pairwise is not enough). L1 logistic reaches < 0.98 x the tree AUROC on >= 8 of 17 (the dependence is not a
   pairwise Ising model), while the K <= 20 mixture does better than L1 logistic on >= 12 of 17.
P4 (values do not explain it). On eICU, MIMIC-IV, NHANES and road safety, mean AUROC(values) <= 0.70 while
   mean AUROC(panels_tree) >= 0.85, and AUROC(both) - AUROC(values) >= 0.15.
P5 (low dimension). The smallest K reaching 95% of the tree AUROC is <= 20 on >= 12 of 17, while those datasets have
   at least 15 realised panels.

## Claim selection
P1 holds -> the fact violates causal sufficiency over the indicators (a latent common parent), so MissDAG's
ignorability and MissNODAG's no-unmeasured-confounding assumptions are the ones contradicted, and Strobl/Tu/Liu are
violated only in the sense that their graphs cannot represent the data-generating process.
P1 fails and P3's first half holds -> the fact violates the no-R->R-edge assumptions directly (Strobl A1, Tu's
leaf-node property, Liu-Constantinou A1), and higher-order structure is needed beyond a pairwise Ising model.

## Withdrawal (the genuine kill)
(a) If AUROC(panels_tree) < 0.70 on average on >= 6 datasets, the panel-level dependence is not what Result 209
    measured at column level, and this experiment does not speak to it; report and stop.
(b) If P4 fails, values do explain the dependence after all and Result 209's second half is an artefact of the
    column-level panel exclusion; that would be a correction to Result 209 and must be reported as one.

## Disclosure (appended 2026-09-06 18:40, after the freeze, before the farm run)
Smoke on dugong, sweep_42093 only (a non-clinical set, 11 panels): the K=10 mixture matched the unrestricted tree on
nine of eleven panels (e.g. 0.967 vs 0.968, 0.797 vs 0.806) and beat L1 logistic on all eleven; values reached 0.999
on one panel and 0.72-0.88 elsewhere. Seen before the farm run; predictions were not edited.

## Amendment 1 (2026-09-06 20:20, before any outcome was scored)
The site-alignment branch used `mimic_split.dev_mask` for MIMIC-IV, but the regime matrix carries its own hash split
(`screen_candidates.dev_mask` on its own name), which is the one `load_full` uses; the mismatch crashed the MIMIC-IV
job with an index error. Fixed to use the regime matrix's own split for both databases; the eICU job was already
correct and is unaffected. No criterion changed.

## Outcome (2026-09-06 20:35; 17/17 datasets, fit on dev, evaluated on holdout; scorer `experiments/score_rrstruct.py`)

P1 HOLDS 17/17, P2 HOLDS, P5 HOLDS 17/17. P3 FAILS, P4 FAILS, and the registered kill (a) FIRES.

**P1.** A Bernoulli mixture with at most 20 classes reaches at least 0.95 of the unrestricted tree's AUROC on every
dataset (ratio 0.954-1.001). Wherever panel presences depend on each other, that dependence is fully explained by a
low-dimensional latent class, with no direct indicator-to-indicator edges needed. The smallest K reaching 95% is <= 20
everywhere (P5), and <= 10 on 15 of 17, against pattern counts in the hundreds or thousands.

**P2.** The classes recovered from the mask alone line up with the institution: on eICU, class purity for hospital is
5.82x the majority baseline with adjusted mutual information 0.382; on MIMIC-IV, purity is 2.01x. The latent regime is
not an abstraction, it is the hospital.

**Claim selection, per the registered rule.** P1 holding selects the first horn: the fact contradicts causal
sufficiency over the missingness indicators. A latent common parent of every indicator is exactly what MissDAG's
ignorability and MissNODAG's no-unmeasured-confounder assumption exclude. Strobl (2018) A1, Tu et al. (2019)'s
leaf-node property and Liu & Constantinou (2022) A1 are violated in the weaker sense that their graphs cannot
represent this process, not because direct edges are present.

**P3 FAILS (1/17, needs 8).** L1 logistic reaches within 2% of the tree on 16 of 17: the dependence is pairwise, with
no higher-order structure. That is consistent with P1, since a low-dimensional mixture induces approximately pairwise
dependence, but it is a registered failure and the "pairwise is not enough" clause is withdrawn.

**P4 FAILS (3/4 on the first clause).** On the four regime-driven sets, panels_tree >= 0.85 on 4/4 and
both - values >= 0.15 on 4/4, but values <= 0.70 on only 3 of 4: road safety is 0.713 against a registered 0.70. The
conjunction fails on 0.013 AUROC. Reported as a failure, not reinterpreted.

**Kill (a) FIRES: panels_tree < 0.70 on 7 of 17.** Per the registered rule this experiment does not speak to Result
209 as that result was phrased, and the reason is now identified: Result 209's statistic fed the model the
MEAN-IMPUTED VALUES of out-of-panel columns, not their indicators. The correction and its replacement claim are
registered separately in prereg/RRMIRROR.md, with confirmation on the mirror split.

Scorer output, verbatim:

```
=== RRSTRUCT (17/17 datasets) ===
P1 best mixture K<=20 >= 0.95 x tree on 17/17 (needs >= 12): HOLDS
P2 eICU purity/majority 5.82 (>= 3) AMI 0.382 (>= 0.15); MIMIC purity 2.01 (>= 1.5): HOLDS
P3 L1 < 0.98 x tree on 1/17 (needs >= 8) and mixture > L1 on 8/17 (needs >= 12): FAILS
P4 on the four regime sets: values <= 0.70 (3/4), panels_tree >= 0.85 (4/4), both - values >= 0.15 (4/4): FAILS
P5 smallest K reaching 95% of tree is <= 20 on 17/17 (needs >= 12); of those, 4 have >= 15 panels: HOLDS
kill (a): panels_tree < 0.70 on 7/17 (kills at >= 6): FAILS
                    values  panels_tree  panels_l1   both  lca_best20  ratio  K_needed  panels
cand_acs_income      0.991        0.854      0.851  0.994       0.853  0.999         5      11
cand_airbnb          0.861        0.678      0.671  0.896       0.678  1.001         2       4
cand_eicu_regime     0.523        0.927      0.910  0.927       0.885  0.954        20      30
cand_higgs           0.998        0.753      0.753  0.998       0.753  1.000         2       3
cand_mimic4_regime   0.562        0.933      0.928  0.934       0.923  0.989        10      22
cand_nhanes          0.693        0.887      0.886  0.927       0.883  0.996         5      15
cand_porto           0.930        0.731      0.731  0.987       0.731  1.000         2       5
sweep_41275          0.908        0.573      0.572  0.912       0.573  1.000         2       3
sweep_42080          0.887        0.513      0.513  0.888       0.513  1.000         1       2
sweep_42093          0.831        0.829      0.805  0.906       0.826  0.997         5      11
sweep_42136          0.866        0.633      0.633  0.879       0.633  1.000         2       4
sweep_42333          0.949        0.955      0.946  0.978       0.952  0.996        10      18
sweep_42737          1.000        0.883      0.879  1.000       0.883  1.000         5       8
sweep_42739          0.713        0.872      0.869  0.943       0.868  0.996        10       9
sweep_46654          0.821        0.507      0.507  0.821       0.507  1.000         1       2
sweep_46703          0.817        0.508      0.508  0.817       0.508  1.000         1       2
sweep_46725          0.864        0.640      0.640  0.878       0.640  1.000         2       3
```
