# Steering probes (development halves only; declared 2026-09-04 23:10 before any run)

Purpose: the user asked for a night of experiments that could steer the research after the edge hunt closed
(Results 187--192). These are DEVELOPMENT-HALF probes with declared predictions, not holdout tests: a probe that
looks positive earns a pre-registration on holdout data; nothing here enters a paper as a result. Runner
`experiments/steer_probes.py`; outputs `results/steer/<probe>_<dataset>.csv`; jobs `queue/pending/STEER-*.json`,
priority 3 (behind the road-safety and eICU seeds and the HCAL2 comparator). Datasets: sweep_42739 (road safety),
mimic4 (first stays), cand_acs_income, cand_nhanes, cand_mimic4_regime, cand_higgs, cand_airbnb, cand_porto; one seed,
three folds, capped at 40,000 dev rows. Arms unless stated: tuned indicator LR, the CV hierarchy (family_cv), a
default native tree (guarded).

| probe | question | prediction (what would make it worth a holdout test) | kill |
|---|---|---|---|
| smalln | does the hierarchy win when training data are scarce (n = 500 ... 20,000)? | family_cv above the tree by >= 0.01 AUPRC at n <= 1,000 on >= 4 of 8 datasets, crossover between 2,000 and 5,000 | tree ahead at every n on >= 6 datasets |
| worstpat | does shrinkage protect the worst-served pattern (per-pattern log-loss / AUPRC, patterns with >= 50 test rows)? | family_cv has the lowest worst-pattern log-loss on >= 4 of 8, and better small-pattern (support < 300) mean log-loss than the tree on >= 5 of 8 | tree best on worst-pattern log-loss on >= 5 of 8 |
| drift | does the lattice statistic (share of records with no fitted training pattern) detect a schema drift sooner than prediction-shift statistics on the tree? | lattice delay 0 windows on every dropped variable; mean-shift or KS delay >= 2 windows or undetected on >= half | prediction-shift detects at delay 0 as often as the lattice |
| abstain | is lattice support a useful abstention score against the tree's own confidence? | expected NEGATIVE: confidence-ranked retention has higher retained-set AUROC than support-ranked at every coverage on >= 6 of 8 (amended 00:20 from AUPRC, which is prevalence-confounded on a retained subset: the v1 run showed confidence "losing" on MIMIC and NHANES only because it retains confident negatives) | support-ranked >= confidence-ranked on >= 4 |
| blend | do tree and hierarchy make complementary errors? four combinations | blend_cv or hier_on_tree_logit above the tree by >= 0.003 on >= 4 of 8 (and never below by > 0.003) | no combination clears +0.003 on more than 2 |
| robust | which arm degrades least when 10 / 30 % of observed test values are dropped? | family_cv loses less AUPRC than the tree at 30 % on >= 5 of 8 | tree loses less on >= 5 |
| transfer (mimic4) | leave-one-site-out: which arm loses least under site shift (transfer minus in-site CV)? | family_cv's transfer gap smaller than the tree's on >= 6 of the sites | tree's gap smaller on >= 6 |

Reading rule: report each probe by its own line above, NEGATIVE first. A probe that passes gets a holdout
pre-registration written the next day, with the SAME criterion; nothing is re-cut after seeing the numbers.

## Outcome (appended 2026-09-05 13:30; scorer `experiments/score_steer.py`; worstpat has 6 of 8, the rest are complete)

NEGATIVE first.
- robust: KILLED. At 30 % extra test-time missingness the hierarchy loses 0.21--0.47 AUPRC on every dataset (Porto 0.013), the
  tree 0.005--0.13; the tree loses less on 8/8. The mechanism is the projection limitation: new observed sets fall outside every
  fitted pattern.
- transfer (MIMIC-IV sites, leave-one-site-out): KILLED. The tree's transfer gap is smaller on 6/7 sites; on three sites the tree
  transfers BETTER than its in-site CV (it profits from the larger training pool), the hierarchy never does.
- abstain: NEGATIVE as declared for the lattice: support-ranked retention is within 0.01 AUROC of random retention on every
  dataset; it is never a useful abstention score. (Aside, not pursued: on the low-prevalence sets the tree's own |p - 0.5| is a
  WORSE retention score than random in AUROC, because it retains confident negatives; a tree-confidence artefact, not ours.)
- smalln: FAILS its line. The hierarchy is >= tree + 0.01 at n <= 1000 on 2/8 (NHANES n=500: 0.372 vs 0.314; MIMIC first stays
  n=500: 0.308 vs 0.263), and on both the tuned indicator LR is above the hierarchy (0.427, 0.315). Small n favours linear models,
  not the hierarchy in particular; the tree is ahead at every n on 4/8 (road safety, Higgs, Airbnb, ACS).
- worstpat (8/8, final 14:00): KILLED. Tree has the best worst-pattern log-loss on 6/8, the hierarchy on 1 (NHANES), the
  indicator on 1 (Porto); small-pattern mean log-loss better than the tree on 1/8. Shrinkage does not protect the worst-served
  pattern; the tree's leaves already pool small patterns with their neighbours.
- blend: MISSES by one. hier_on_tree_logit (the CV hierarchy fitted on [X, tree OOF logit]) is never below the tree by more than
  0.003 and clears +0.003 on 3/8 (needed 4): MIMIC regimes +0.0047, NHANES +0.0079, MIMIC first stays +0.0038; blend_cv clears on
  1 (NHANES +0.0078), never worse; blend50 and stack_tree_on_hier are worse on 5 and 3. Post hoc: the three clears are the three
  clinical many-pattern sets, and this construction is the calibration wrapper (HCAL) with full per-pattern coefficients rather
  than two Platt parameters. Not carried forward under this registration; if it is ever tested it needs its own line on holdout
  halves and must be compared against HCAL, not the tree alone.
POSITIVE.
- drift: PASSES. The lattice statistic (share of records whose observed set matches no fitted training pattern) detects a
  dropped well-observed variable at delay 0 on 32/32 (dataset, variable) cases; the tree's mean-prediction shift and KS statistic
  are at delay >= 2 or never fire on 57/64. Expected, since the statistic is built to see exactly this drift, but it is the
  monitoring quantity the deployment checklist already names and this is the first measurement of it. Candidate for a holdout
  pre-registration with a broader drift family (unit changes, added variables, prevalence shift) where the lattice statistic is
  NOT expected to fire, so that the test can fail.

Steering reading: after the night, the hypergraph's defensible uses are (1) the diagnostic and structural account already in the
paper, (2) the drift statistic (monitoring, not prediction), and (3) at most a calibration/stacking wrapper around a tree whose
gain is confined to clinical many-pattern data and is small. Prediction against a native tree is closed on every axis tried:
pooled accuracy, small n, worst pattern, robustness, site transfer, abstention, routing, residual boosting, coverage.
