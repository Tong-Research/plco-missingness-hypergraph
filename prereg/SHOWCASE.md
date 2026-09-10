# Pre-registration: mechanism-chosen showcase candidates (APPROVED by the user 2026-09-04 09:05, "Try all these")

Written 2026-09-04 09:08 BEFORE any of these datasets was downloaded, screened or compared. Same protocol as
PORTO/HIGGS/ACS and SWEEP: hash split, diagnostics on the development half only, predictions per dataset added by
dated amendment after the screen and before the holdout run, all arms of run_candidate.py (published estimator,
own-rows arms, family_cv, tuned imputation/indicator/interaction, tree), permuted-mask nulls, 0.002 floor.
These candidates are chosen by MECHANISM (missing means "does not apply"; a linear model is the conventional
deliverable in the domain) and are reported in Table sweep with the dagger and their provenance, never as a sweep.

Candidates declared now:
  A. Inside Airbnb listings, five cities pooled (London, Los Angeles, New York City, Paris, Sydney; the current
     snapshots on insideairbnb.com/get-the-data at 09:05). Review scores, host response/acceptance rates and
     superhost status are missing for new hosts. Target: nightly price above the city's median (binary).
     Non-numeric columns coerced to NaN; identifiers and free text dropped; city kept as an integer code.
  B. US real-estate listings by zip code (OpenML 43631, 974,066 rows, 34 features, 17.5% missing). Lot size,
     year built and bath counts are absent for land and some condominium listings. Target: price above the
     overall median (binary; declared here to avoid a per-zip choice).
  C. Home Credit default risk (Kaggle): BLOCKED, no API token on this machine. Recorded as not run unless a
     token is supplied; not to be replaced by another hand-chosen dataset.
  D. Semi-synthetic on real masks (a mechanism demonstration, not a showcase): keep the real observed values
     and missingness patterns of the Higgs and road-safety development halves, regenerate the outcome from a
     logistic model whose coefficients differ by pattern by a controlled amount delta in {0, 0.25, 0.5, 1};
     report every arm's AUPRC against delta. Prediction: the own-rows hierarchy's gain over tuned imputation
     and the indicator increases monotonically with delta and is within the floor at delta = 0; the published
     support rule's gain does not increase with delta on Higgs (its regimes are disjoint).

Predictions for A and B follow their screens, by amendment, before their holdout runs.

## Amendment 2026-09-04 09:20: Airbnb screened (dev 60,000: iota 0.165, cov30 0.9995, H 0.40 / null 0.12 / H_exc +0.28,
tuned imputation 0.8798 vs indicator 0.8871, +0.0073; 26 patterns; prevalence 0.499) -> FLAGGED. Predictions for the holdout
half (about 93,000 listings, 3 x 5 cells), written before the run:
P1 family_cv - tuned imputation >= 0.002 (p < 0.05) with real - null excess >= 0.002 (larger-null-gain control).
P2 family_cv - tuned indicator >= 0.005 (the showcase bar). Honest expectation: uncertain; the indicator gain on the dev
   half is small (0.007) and the new-host regime may be captured by the indicator alone.
P3 published estimator - imputation within +-0.005 (26 nested-ish patterns: neither rule should dominate strongly).
P4 tree - family_cv >= 0.01 (nonlinearity in price).
Withdrawal: P1 fails -> no claim; P2 fails with P1 holding -> "beats imputation, not the indicator", as on ACS.

## Note 2026-09-04 09:25: candidate B withdrawn before screening. OpenML 43631 is not a listing-level table: its rows are
zip code x month aggregates (median listing price, active listing count, days on market, with month-over-month and
year-over-year changes), so its missingness is reporting gaps, not "does not apply" fields of a listing. The declared
mechanism does not exist in it. It is not screened and not replaced by a hand-chosen substitute (same rule as C).

## Outcome, Airbnb (appended 2026-09-04 09:30; results/cand/cand_airbnb.csv, 15 cells, holdout 93,596)
means: tree 0.9392, family_cv = exact_cv = own-rows k=0 0.8864, interaction 0.8827, indicator 0.8824, submodels 0.8770,
published 0.8754 (projected 0.8755), imputation 0.8749. family_cv chose the own-rows rule in 15/15 (kappa 10 in 11).
P1 HOLDS (+0.0119, p 6e-5, excess +0.0129). P2 FAILS by 0.001 (+0.0040 over the indicator against the 0.005 bar; p 6e-5;
+0.0037 over the interaction expansion). P3 HOLDS (published +0.0004). P4 HOLDS (tree +0.0535).
Reading: a win over imputation and a small, significant edge over the indicator that does not reach the bar this file
set; reported as "beats imputation; ahead of the indicator by 0.004". Consistent with the sweep: the own-rows hierarchy
is the best linear model here, and the tree is well ahead.

## Outcome, item D (appended 2026-09-04 09:37; results/semisynth_cand_higgs.csv, results/semisynth_sweep_42739.csv; tables/semisynth.tex)
Higgs masks (6 patterns): CV hierarchy - imputation -0.002, +0.009, +0.037, +0.094 at delta 0, 0.25, 0.5, 1; over the indicator
-0.002, +0.009, +0.035, +0.087; the published support rule -0.040, -0.036, -0.023, -0.006 (below imputation throughout);
at delta 1 the own-rows hierarchy beats the tree (0.719 vs 0.694). Road-safety masks (986 nested patterns): CV hierarchy
-0.011, -0.010, +0.011, +0.064; it chose the support rule at delta 0 and 0.25 and the own-rows rule at 0.5 and 1; at
delta 1 it beats the indicator by 0.066 and the tree by 0.043.
Prediction D: the monotone rise HOLDS on both mask sets and the published rule's flatness HOLDS on Higgs; the "within the
floor at delta = 0" clause HOLDS on Higgs masks (-0.002) and FAILS on road-safety masks (-0.011): on many nested patterns a
pattern hierarchy pays an entry cost when there is no heterogeneity to exploit. Reported as such.

## Amendment 2026-09-04 14:30 (APPROVED by the user 11:11 "Screen clinical" / 14:26 "Let go with all machines"): clinical candidates declared BEFORE download or build

Same protocol. Mechanism: "does not apply" missingness inside clinical data, as opposed to "not ordered".
  E. NHANES with NCHS linked mortality (continuous cycles 1999-2018, adults 18+). Laboratory panels are assigned by
     survey design (fasting subsample; age-gated exams), so patterns are large and by design. Target: death within 5 years
     of the exam among those with mortality follow-up (binary). Demographics, examination (BMI, blood pressure) and
     laboratory columns kept with their design blanks; identifiers, weights and strata dropped.
  F. MIMIC-IV first-ICU-stay treatment-regime matrix: the 42 first-24h labs of the published matrix PLUS treatment
     variables that exist only for treated patients (first-24h ventilator settings, vasopressor dose, dialysis
     parameters, from chartevents/inputevents) kept as NaN when the treatment did not occur. Target: in-hospital
     mortality. Hash split keyed "mimic4_regime" so its dev/holdout halves are independent of every earlier MIMIC probe.
  G. eICU first-ICU-stay treatment-regime matrix, built the same way from its treatment tables, keyed "eicu_regime".
Predictions per candidate follow their screens, by amendment, before their holdout runs. Flag rule unchanged.
Machines: builds on the host holding the raw files; screens and holdout comparisons dispatched over pilot, spinner,
orca and dugong by the queue runner.

## Note 2026-09-04 14:40: candidate G (eICU treatment regimes) BLOCKED. The local eICU copy holds only patient, hospital
and lab tables; the treatment tables (treatment, infusionDrug, respiratoryCharting) are not downloaded and need the
credential holder. Recorded as not run unless those files are supplied; not replaced.

## Amendment 2026-09-04 15:00: F (MIMIC-IV treatment regimes) screened -- NOT flagged; run anyway as an unflagged row
Built on pilot: n 66,989, d 57 (42 published columns + 7 ventilator, 7 infusion, 1 RRT), 37.3 % missing, 9,448 patterns;
ventilated 34,926, any vasopressor 22,971, RRT 1,387. Dev half (33,458): iota 0.269, cov30 0.547 (the treatment fields
fragment the patterns), H 1.63 / null 1.52 / H_exc +0.11, tuned imputation 0.3876 vs indicator 0.4376 (+0.050).
Not flagged (coverage and H_exc both below the rule). Run on the holdout half anyway, as the sweep does for unflagged
datasets, with the honest expectation written first: P1 indicator - imputation >= 0.03 (treatment presence is strongly
informative and the indicator carries it); P2 published estimator - imputation <= 0 (coverage 0.55: many records fall to
ancestors); P3 family_cv chooses the support rule in a majority of cells and lands within 0.01 of the published estimator;
P4 no hypergraph arm beats the indicator. Dispatched to spinner.

## Amendment 2026-09-04 16:05: G (eICU treatment regimes) UNBLOCKED -- treatment, infusionDrug, respiratoryCharting and
respiratoryCare tables supplied by the credential holder at 16:02 and placed beside patient/hospital/lab. Build rule,
declared before running: cohort and row order of eicu_sites._cohort (asserted against the cached matrix); ventilator
settings = the seven most frequent numeric respchartvaluelabel entries within respcharttypecat "respFlowSettings" in the
first 24 h (mean per stay; NaN if never charted); infusions = max drugrate in the first 24 h for drugname containing
norepinephrine, epinephrine, vasopressin, phenylephrine, dopamine, dobutamine, insulin (NaN if none); renal replacement
= hours from unit admission to the first treatmentstring containing "dialysis" or "CRRT" within 24 h (NaN if none).
Screen, then predictions by amendment, then holdout. Built on pilot (DUA: raw files stay here).

## Amendment 2026-09-04 16:50: E and G screened; predictions before their holdout runs
E. NHANES (built on orca: n 29,625 adults with 5-year follow-up, d 52, prevalence 0.072, 11.7 % missing, 593 patterns;
   HSCRP unavailable before 2015 -> NaN by cycle, stated). Dev half (14,910): iota 0.230, cov30 0.908, H 0.89 / null 0.69 /
   H_exc +0.20, tuned imputation 0.4714 vs indicator 0.5789 (+0.107). FLAGGED. Predictions (holdout ~14,700, 3 x 5):
   P1 family_cv - tuned imputation >= 0.002 with null excess >= 0.002.
   P2 family_cv - tuned indicator >= 0.005 (showcase bar). Honest expectation: the mask itself carries a large part of
      the signal (non-response and design subsampling relate to mortality), so this is uncertain; a tie is the likelier
      outcome.
   P3 published estimator - tuned imputation within [-0.02, +0.06] (design patterns are large; the support rule may do well).
   P4 tree - family_cv >= 0.01.
   Dispatched to orca.
G. eICU regimes (n 95,197, d 57, 48.0 % missing, 35,188 patterns; ventilated 52,157, any infusion 18,021, RRT 3,371).
   Dev half (47,496): iota 0.258, cov30 0.199, H_exc +0.15, imputation 0.3462 vs indicator 0.3669 (+0.021). NOT flagged
   (coverage 0.20). Run anyway as an unflagged row, expectations as for F: indicator - imputation >= 0.015; published -
   imputation <= 0; family_cv picks support in a majority; no hypergraph arm beats the indicator. Dispatched to dugong.

## Outcomes, E and F (appended 2026-09-04 18:45; results/cand/cand_nhanes.csv, cand_mimic4_regime.csv, 15 cells each)
E. NHANES holdout (14,715): tree 0.5661, indicator 0.5590, interaction 0.5588, family_cv 0.4848 = submodels 0.4848, published
   0.4832, imputation 0.4582, exact_cv 0.3672. P1 HOLDS (+0.0218 over imputation, p 3e-4, null excess +0.0202). P2 FAILS
   (-0.0767 against the indicator; the indicator is +0.0951 over imputation: the mask is the signal, as the honest
   expectation said). P3 HOLDS (published +0.0205, inside [-0.02, +0.06]). P4 HOLDS (tree +0.0801). family_cv chose the
   support rule in 15/15 (kappa 0 in most); the own-rows rule loses 0.089 to imputation here (design patterns are nested
   by cycle and subsample, not disjoint regimes).
F. MIMIC-IV regimes holdout (33,531): tree 0.4686, interaction 0.4319, indicator 0.4318, family_cv 0.3934 = submodels, published
   0.3929, imputation 0.3879, exact_cv 0.3191. P1 HOLDS (indicator +0.0441). P2 FAILS narrowly (published +0.0062 over
   imputation, p 0.02, not <= 0); its null excess is +0.0009, below the floor, so the table records no win. P3 HOLDS (support
   rule 15/15, within 0.01). P4 HOLDS (no hypergraph arm within 0.039 of the indicator).
Reading: in clinical data the missingness mask is strongly informative and an indicator carries it; treatment-defined
missingness fragments patterns; neither gives the few-large-regimes structure. G (eICU regimes) pending on dugong.

## Outcome, G (appended 2026-09-05 13:45; results/cand/cand_eicu_regime.csv, 15 cells merged from three per-seed files)
G. eICU regimes holdout (47,701): tree 0.4029, interaction 0.3707, indicator 0.3699, imputation 0.3362, projected 0.3212,
   submodels 0.3206, family_cv 0.3205, published 0.3198, exact_cv 0.1734. Expectations as registered: indicator - imputation
   >= 0.015 HOLDS (+0.0342, p 6e-5; null excess +0.0402); published - imputation <= 0 HOLDS (-0.0158); family_cv picks support in a
   majority HOLDS on the evidence available (5/5 cells with a surviving log, seed 1; the seed 0 and 2 logs were lost with the
   laptop runner, but family_cv equals pattern_submodels to 0.0001, which is the support rule at kappa 0); no hypergraph arm beats
   the indicator HOLDS (best hypergraph arm 0.0487 below it). Tree 0.0322 above the best linear arm. Table row: unflagged, LOSS
   (the hierarchy is 0.016 below tuned imputation, the largest loss in the table beside road safety's own-rows collapse).
   Run note: the job died twice with hung ssh sessions (2026-09-04 19:36, 2026-09-05 00:52) and once with the laptop's runner at
   session teardown; finished as three per-seed jobs with --resume on dugong, spinner and the laptop; merged by
   experiments/merge_seed_files.py.
