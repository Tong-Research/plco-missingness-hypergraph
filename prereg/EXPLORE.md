# EXPLORE: a frozen battery for hunting a new empirical fact (registered 2026-09-06 16:10)

This is EXPLORATORY. It registers no prediction. It registers the battery and the rule for what may become a fact.

## Battery (`experiments/probe_explore.py`, frozen before any output is read)
Per dataset on the DEV half (cap 60,000; 3-fold stratified CV seed 0; HCAL tree config):
- Dataset level: n, p, prevalence, pattern count, singleton share, mean support fraction, mask entropy, mask rank at
  90% variance, count of columns with missingness; AUPRC of native tree, native + explicit mask, mask-only tree,
  support-size-only tree, tuned mean-imputed LR; mask gain, mask-only lift and support-only lift over prevalence,
  tree minus LR; between-pattern and between-support-decile shares of outcome variance; Spearman(support, y);
  across patterns with support >= 100: Spearman(support, per-pattern AUPRC), Spearman(support, lift),
  Spearman(observed count, prevalence), AUPRC range, max |calibration gap|; across columns: Spearman(missing rate,
  permutation importance), Spearman(missing rate, |corr(x, y)|), median recoverability, median |Spearman(x, support)|.
- Column level and pattern level tables with the ingredients above.

## Rule
Any regularity seen in the dev output is only a CANDIDATE. To become a fact it must be written as a prediction with a
threshold in a separate prereg (EXPLORE-CONFIRM.md) BEFORE the same battery is run on the HOLDOUT halves, and it must
hold there. Dev-slice replication never counts. Statistics added to the battery after reading output are declared
as amendments.

## Amendment 1 (2026-09-06 16:15, before any dev output beyond the sweep_46654 smoke was read)
Added to the battery, to measure a structure other than the pattern hypergraph: (i) policy sparsity: for each column
with missingness, the AUROC for predicting its indicator from the single best and the three best other columns
(chosen by permutation importance), i.e. how few columns the measurement decision depends on; (ii) panel structure:
the number of distinct indicator columns (exact) and of clusters at Jaccard >= 0.9 among missing sets, i.e. how many
order sets generate the mask. Motivation: the recoverability result says the mask is a function of the values; the
question is whether that function is sparse and panel-structured (a measurement-policy graph) rather than a hypergraph.

## Amendment 2 (2026-09-06 16:20, after reading four dev rows: ACS income, Airbnb, Higgs, sweep_42136)
Those rows show recov_top1 = 1.0 on three datasets: a single other column predicts each indicator perfectly. That is
co-missingness within a panel leaking through the fill value, not a measurement decision driven by values. Added
`experiments/probe_explore2.py`: recov_full (predict M_j from always-observed columns only, which cannot leak any
mask) and recov_outpanel (from columns outside j's Jaccard >= 0.9 cluster). This is the statistic that separates
"values decide the measurement" from "panels decide it". Declared before any of its output was read.

## Amendment 3 (2026-09-06 16:30, after reading the amendment-2 dev output for all 17)
Amendment 2 shows two regimes: on non-clinical sets the always-observed columns predict each indicator at AUROC 0.8-1.0;
on eICU, MIMIC-IV, NHANES and road safety they predict at 0.52-0.62 while other panels' columns predict at 0.94-0.97.
ICU sets have only two always-observed columns, so that test is weak there. Added `experiments/probe_explore3.py`,
the cascade test: among rows where another panel is fully observed, predict M_j from that panel's VALUES only (no
mask leak possible), and separately from that panel's presence alone. Declared before any of its output was read.
