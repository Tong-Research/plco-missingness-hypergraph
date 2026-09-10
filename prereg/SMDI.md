# SMDI: does the single-model diagnostic give the same answer as measuring the blocks separately? (pre-registered 2026-09-06 21:10)

Required by `papers/PAPERA-DUP-DISSOCIATION.md`. The closest prior work, `smdi` (Weberpals et al., JAMIA Open 2024,
doi:10.1093/jamiaopen/ooae008), already fits ONE model per column predicting its missingness indicator from covariates
AND the other columns' missingness indicators together, and reads the answer off variable importance. Our measurement
fits the two blocks SEPARATELY and reports the difference of their areas under the curve. A referee will say the
single model's importance plot already tells you which block wins. This experiment tests that.

## Design (`experiments/probe_smdi.py`)
The 17 registered datasets, RRSTRUCT's panels, splits, representative columns and tree, unchanged. For each panel with
always-observed columns available: auroc_values and auroc_panels (each block fitted alone, dev to holdout), auroc_both
(one model on both blocks, the smdi construction), and the permutation importance of each block inside that single
model, summed over its columns and floored at zero, for three seeds. imp_share_values is the values block's share.

## Predictions
P1. Masking. At least 10 panels have a block with standalone AUROC >= 0.80 that receives <= 10% of the importance in
    the single model.
P2. Disagreement. The regime call from importance, sign(imp_share_values - 0.5), disagrees with the call from
    standalone AUROC, sign(auroc_values - auroc_panels), on at least 2 datasets.
P3. Instability. Among panels where |auroc_values - auroc_panels| <= 0.05, the sign of (imp_share_values - 0.5)
    differs across the three seeds on at least 20%.
P4. Complementarity. auroc_both >= max(auroc_values, auroc_panels) + 0.01 on at least 30% of panels, so the single
    model conflates two sources that are individually distinguishable.

## Withdrawal, stated plainly
If all four fail, the single-model diagnostic answers the same question as ours and our contribution reduces to
interpretation and to the dataset-level partition. That weakens the paper and will be written as such, not hidden:
the abstract would then claim the partition and the mirror-split stability only, and would credit smdi with the
measurement. If P1 or P3 holds the decomposition is doing work the single model cannot, which is the claim the paper
needs against its nearest neighbour.

## Outcome (2026-09-06 21:40; 17/17 datasets, 152 panels with both blocks; scorer `experiments/score_smdi.py`)

**P1 HOLDS (20 panels, needs 10). P2, P3 and P4 FAIL.** Per the registered rule, P1 holding means the decomposition
does work the single model cannot, and that is the claim the paper needs against its nearest neighbour.

The 20 panels are the demonstration. On sweep_42333, seven panels have BOTH blocks predicting at 0.90 or better on
their own, and the single model's importance share for the values block across them runs 0.999, 1.000, 0.977, 0.010,
0.001, 0.002, 0.039. Same dataset, same construction, near-identical standalone performance, and the split is
essentially arbitrary. On ACS income and NHANES the values block takes the entire importance while the other panels
alone would predict at 0.86 to 0.99; on sweep_42093 the reverse, with the values block at 0.83 standalone receiving
6% of the importance. So where both sources are individually informative, which is common, the importance split is
decided by redundancy rather than by how much each source explains, and it cannot be read as an answer to "what
determines this column's missingness".

**The three failures, reported as failures.** P2: the dataset-level regime call from importance disagrees with the
call from standalone AUROC on only 1 of 17, so at the level of a whole dataset the single model usually reaches the
same verdict. P3: the importance sign is perfectly stable across the three seeds, on 0% of the 34 near-tied panels,
so the arbitrariness above is systematic rather than stochastic; the instability argument is withdrawn. P4: the
single model beats the better block by at least 0.01 on 24% of panels against a registered 30%.

The paper therefore claims the panel-level result and not the dataset-level one, and says so.
