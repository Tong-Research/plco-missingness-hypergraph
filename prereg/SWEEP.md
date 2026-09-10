# Pre-registration: rule-based dataset sweep to validate the diagnostic on real data (APPROVED by the user 2026-09-04 00:13, "sweep")

Written 2026-09-04 00:14 BEFORE the candidate list was pulled. The list is produced mechanically by the rule
below; no dataset is added or removed by hand after this file is committed, except by the exclusion rules
stated here, each of which must be recorded with its reason in the log.

## Selection rule (OpenML, queried once)

Active datasets with NumberOfInstances >= 100,000, NumberOfMissingValues / (instances x features) >= 0.05,
NumberOfFeatures <= 100, and either NumberOfClasses == 2 (binary target) or NumberOfClasses == 0 with a numeric
default target (binarised at its median, declared here). Ordered by NumberOfInstances descending; the first 15
distinct names are the sweep. Exclusions, applied mechanically and logged: (x1) a second dataset whose name
differs from an earlier one only by suffix/version; (x2) fewer than 5 numeric columns with any missingness
after coercing non-numeric columns to NaN (the method needs patterns over numeric variables); (x3) a
download or parse failure after two attempts; (x4) datasets already used in this project (mimic*, eicu*,
physionet*, the eleven public sets, cand_*). An excluded dataset is replaced by the next by size.

## Screen (development half, hash split, 60,000 subsample)

`experiments/screen_candidates.py`: iota, support-30 coverage, H, H_null, H_exc, tuned imputation vs tuned
indicator. Flag rule (unchanged from Result 170): H_exc >= 0.15, cov30 >= 0.9, iota >= 0.05.

## Comparison (holdout half, 100,000 subsample, 2 seeds x 5 folds), on EVERY sweep dataset, flagged or not

`experiments/run_candidate.py`: tuned imputation, tuned indicator, mask interaction, tree (defaults), pattern
submodels, ours, ours projected; permuted-mask nulls. Outcome per dataset: WIN if ours - tuned imputation
>= 0.002 (paired median, p < 0.05) AND real - null excess >= 0.002; else NO WIN.

## Predictions (the diagnostic's claim, as a 2x2 over the sweep plus the three earlier candidates)

P1 Among flagged datasets, the WIN rate is >= 0.6. P2 Among unflagged datasets, the WIN rate is <= 0.2.
P3 The flag rate over the sweep is below 0.7 (if it is not, the rule is too permissive and P1 is uninformative;
   this is recorded as a finding about the rule). P4 On no dataset does ours beat the tuned indicator by >=
   0.005 unless it is flagged (indicator wins are reported per dataset either way).

## Withdrawal / reporting

If P1 fails, the diagnostic does not transfer from the synthetic suite to real data and the paper says so in the
diagnostic section, with the table. If P3 fails, the flag threshold is reported as uncalibrated and the 2x2 is
reported with H_exc as a continuous score (AUC of H_exc for WIN) instead. Every screened dataset appears in
the table whatever happened. Bosch, Lending Club and the three candidates of Result 170 are reported alongside
with their own provenance stated.

## Amendment 2026-09-04 00:16 (after the list was pulled, before any dataset was built or screened)

The rule yields 13 datasets, not 15 (results/sweep_list.json, committed with this amendment); the sweep is
all 13, with no replacements available. Two mechanical conditions are added because the OpenML metadata does
not expose them: (x5) no default target attribute in the OpenML description -> excluded (no target can be
declared without a choice by hand); (x6) matrices are capped at 400,000 rows by a fixed random subsample
(seed 0) at build time, before the hash split, for memory. Non-numeric columns are coerced to NaN and dropped
if entirely NaN; nothing else is selected by hand. Every exclusion is logged with the rule that fired.

## Amendment 2026-09-04 00:36 (after the first build pass, before any comparison)

Build pass 1 (results/sweep_exclusions.json): 6 built, 7 excluded -- four because the OpenML default target
has missing values (la_crimes 6 rows, road_safety 23, SoilHydroDB 66,206, public_procurement 199,954), two by
HTTP 500 from OpenML (albert, dgf_6af37c98), one by x2 (methane: no numeric missingness). Excluding a dataset
for six missing target rows is a builder limitation, not the rule's intent, so: (x7) rows with a missing target
are dropped before everything else, and the four are rebuilt; the two HTTP-500 datasets are retried once more
and excluded under x3 if they fail again. Screens already run are not re-run.

## Amendment 2026-09-04 00:41: (x8) non-finite values (inf) are set to NaN at build, mechanically, for every dataset
(federal_election's screen crashed on infinities; it is rebuilt and screened under the same rule as the others).

## Amendment 2026-09-04 01:12: (x9) columns whose maximum absolute value exceeds 1e15 (identifiers parsed as
numbers; public_procurement's contract_number reaches 1e279 and overflows the scaler) are dropped at build,
mechanically, for every dataset. public_procurement is rebuilt and screened; no other dataset has such a column.

## Outcome (appended 2026-09-04 05:40; tables/sweep.tex, tables/sweep_counts.tex, results/cand/sweep_*.csv, Results 176-180)

13 datasets built and compared (10 by the rule after the logged exclusions, plus the three mechanism-chosen candidates).
Flag rate over the 10 sweep datasets 4/10 -> P3 HOLDS (< 0.7).
2x2 over all 13: flagged 7 -> WIN 4 (Higgs [amendment slice], ACS, fps, road_safety), no win 3 (Porto, jigsaw100K, SoilHydroDB;
the last two have near-trivial targets); unflagged 6 -> WIN 3 (wine-reviews, Crime_Data_from_2010, federal_election), no
win 3 (jigsaw 2M, la_crimes, public_procurement).
P1 FAILS narrowly (flagged win rate 0.57 < 0.6). P2 FAILS (unflagged win rate 0.50 > 0.2). P4 FAILS (Crime_Data_from_2010,
unflagged, beats the indicator by 0.020). Verdict: the H_exc >= 0.15 threshold from the synthetic suite does not transfer
to real data; per P3's fallback the sweep is reported as a table, with H_exc as a continuous score beside the outcome.
Every WIN is by the CV-selected hierarchy (own-rows rule chosen in every winning dataset); the published support-rule
estimator wins on none, and on public_procurement every pattern arm loses 0.10 to imputation.

## Amendment 2026-09-04 05:30 (after the comparisons; recorded because the fourth referee pass found it undeclared)

The WIN criterion above names the estimator AS PUBLISHED ("ours"). Timeline: this file was written at 00:14 with that
arm; the PORTO/ACS amendments of 00:38-00:42 added the own-rows and cross-validated arms to run_candidate.py; the sweep
comparisons started at 00:57 with those arms in the runner; the table generator (05:00) scored WIN as "published OR
cross-validated hierarchy" without this file being amended. That widening was not registered before the comparisons.
Both criteria are therefore reported: registered (published arm only) and widened (cross-validated hierarchy, whose
permuted-mask control is the larger of the two fitting rules' null gains, since it has no permuted run of its own).
Registered 2x2 over 13: flagged 2 win / 5 no, unflagged 1 win / 5 no. Widened: flagged 4/3, unflagged 3/3; rule-based
datasets alone: flagged 2/2, unflagged 3/3. The Higgs win is on the amendment's development slice, not a holdout, and is
counted separately (\SweepHiggsSlice). The reporting clause promising Bosch and Lending Club rows is struck: those were
development-half probes (Result 170) with no holdout comparison, and are reported in the log only.

## Amendment 2026-09-04 14:50: more cells for the three wins below 0.015

fps-in-video-games (+0.010), wine-reviews (+0.012) and federal_election (+0.008) were scored on 2 x 5 cells (Wilcoxon
minimum p = 0.002). Each is rerun with 5 seeds x 5 folds (25 cells) on the same holdout subsample; the win stands only
if the paired median stays >= 0.002 with p < 0.01 and the null excess >= 0.002. Prediction: all three medians stay
within 0.004 of their 10-cell values. Dispatched to spinner and orca; the 10-cell files are kept as *.10cells.csv.

## Outcome of the 14:50 amendment (appended 2026-09-04 16:20; 25 cells each, spinner/orca)
fps-in-video-games: +0.0099 (10 cells +0.0095), p 6e-8, null excess +0.0102 -> stands. wine-reviews: +0.0117 (+0.0119), p 6e-8,
excess +0.0120 -> stands. federal_election: +0.0083 (+0.0079), p 6e-8, excess +0.0079 -> stands. All three within 0.001 of
their 10-cell values (predicted within 0.004).

## Amendment 2026-09-04 17:10: the remaining seven sweep datasets to 25 cells (5 seeds x 5 folds) on the same holdout subsamples
(road_safety, Crime_Data_from_2010, SoilHydroDB, jigsaw100K, jigsaw 2M, la_crimes, public_procurement), so that every sweep
row carries 25 cells like the three reruns of 14:50. Prediction: every paired median within 0.004 of its 10-cell value and no
outcome (win / no win / loss) changes. The 10-cell files are kept as *.10cells.csv. Dispatched to trevally (new host, same
environment) and pilot.

## Note (2026-09-05 11:50): road_safety 15-cell file lost, 25-cell rerun replaces it

`results/cand/sweep_42739.csv` (150 rows, 15 cells; the source of the road_safety row committed in a43bee6 at 18:45 on
2026-09-04) was overwritten on the evening of 2026-09-04 by a 30-row partial of the 25-cell T3 rerun that died with a hung ssh
session (the runner's shrink guard did not catch it; the release built at 22:24 carries the 30-row copy). The table row in the
paper was generated before the overwrite and stands. The 25-cell rerun (five per-seed files, merged by
`experiments/merge_seed_files.py`) replaces the file; seeds 0-3 are complete, seed 4 is running on orca, and the row will be
regenerated from all 25 cells when it lands. The release is rebuilt after that.

## Outcome of the 25-cell amendment, road_safety (appended 2026-09-05 18:20)

Five per-seed jobs (`--seed-start 0..4 --resume`, merged by `experiments/merge_seed_files.py`) replace the lost 15-cell file.
25 cells: imputation 0.6013, indicator 0.6264, interaction 0.6264, published 0.6148, family_cv 0.6672, tree 0.8383. The row is
unchanged from the 15-cell version to three decimals; the permuted-mask excess moves +0.064 -> +0.066 and the verdict stays WIN.
P1 HOLDS (+0.0136), P2 HOLDS (+0.0188), P3 FAILS (published 0.0117 below the indicator), P5 inversion as before (own-rows above
the published rule, which is what the CV hierarchy selects: family_cv chose ('exact', 100) in every logged cell). Tree +0.212
above the best linear arm, the table's widest gap.
Run note: the last seed was reported FAIL (rc = -1) at 15:52 because the master lost the poll on a job it had launched detached
8 h earlier; the output file held a complete five-fold set and was verified (5 cells x 15 rows x 10 arms) before merging. The
runner's exit-code path needs the same tolerance as its heartbeat; recorded here rather than fixed mid-run.

## Note (2026-09-08 11:30): public_procurement is the last row of the 17:10 amendment still at 10 cells

The 17:10 amendment took the remaining seven sweep rows to 25 cells. Six landed. public_procurement
(`sweep_42093`) did not, and the table in the paper is still generated from its 10-cell file, which
is why `results/cand/sweep_42093.10cells.csv` and `results/cand/sweep_42093.csv` are the same run.

What is on disk: the original T3 job (`queue/moved-to-dugong/T3-sweep_42093-25cells.json`, trevally,
`--seeds 5`) left `results/cand/sweep_42093.trevally.csv` with 23 of 25 cells -- the collector
renamed it rather than overwrite the 10-cell file, so unlike road_safety nothing was lost. Per-seed
reruns 0-3 (`sweep_42093.s0..s3.csv`, 2026-09-05 20:11) are complete, five folds each. Seed 4 is
missing. This is the same position road_safety was in on 2026-09-05 11:50.

Seed 4 is dispatched now, `--seeds 1 --seed-start 4`, and the five per-seed files are merged by
`experiments/merge_seed_files.py`, which refuses a seed file that is not a full five-fold set and
refuses to shrink the merged file. The 23-cell trevally partial is not merged; it is kept as the
record of the job that died.

The prediction is the one the 17:10 amendment already registered and is not restated more weakly
here: the paired median stays within 0.004 of its 10-cell value and the outcome does not change.
public_procurement's 10-cell outcome is a LOSS (every pattern arm 0.10 below imputation), so the
prediction is that it stays a loss. If the median moves by more than 0.004, or the outcome changes,
that is reported here and in the paper as a finding about a 10-cell verdict, not quietly absorbed.

Withdrawal: if seed 4 cannot be produced, the row stays at 10 cells and the table says so in a
footnote, since every other sweep row carries 25.

Separately, `figures/make_sweep_table.py` accepted any file under `results/cand/` whose name did not
match three named suffixes, so `sweep_42093.trevally.csv` regenerated as an eighteenth dataset with
n_pat -1 and H_exc NaN. It now skips any dotted stem; dataset keys never contain a dot. The
committed table was generated before that file arrived and is unaffected.

## Outcome of the 25-cell amendment, public_procurement (appended 2026-09-08 12:55)

Seed 4 ran on dugong (`queue/submitted-2026-09-08-sweep42093/T3-sweep_42093-25cells-s4.json`,
4,899 s, five folds, exit 0). Merged with `experiments/merge_seed_files.py sweep_42093 5`, which
replaced the 10-cell file: 375 rows, 25 cells, all ten arms. Every sweep row now carries 25 cells,
which is what the 17:10 amendment set out to do; this was its last outstanding dataset.

**The registered prediction holds.** It was that the paired median stays within 0.004 of its
10-cell value and the outcome does not change.

| | 10 cells | 25 cells | moved |
|---|---|---|---|
| imputation | 0.99272 | 0.99232 | $-0.0004$ |
| indicator | 0.99329 | 0.99663 | $+0.0033$ |
| interaction | 0.99554 | 0.99495 | $-0.0006$ |
| published arm | 0.88990 | 0.88852 | $-0.0014$ |
| CV hierarchy | 0.89257 | 0.89099 | $-0.0016$ |
| tree | 0.99996 | 0.99996 | $0.0000$ |
| paired median, published | $-0.10604$ | $-0.10561$ | $+0.00043$ |
| paired median, CV | $-0.10420$ | $-0.10376$ | $+0.00044$ |

Both medians moved by less than 0.0005 against a 0.004 tolerance. The verdict is unchanged: a
LOSS under both the registered and the widened criterion, with every pattern-conditional arm about
0.10 below imputation. The permuted-mask excess moves $+0.0003 \rightarrow +0.0024$, still far
below the 0.002 floor's neighbourhood in the direction that matters (it does not turn a loss into
a win).

`tables/sweep_counts.tex` is byte-for-byte unchanged, so every count the papers quote --
`\SweepWinTotal`, `\SweepTotal`, `\SweepLoss` and the 2x2 -- is unaffected. The only change in
`tables/sweep.tex` is this row, in the third decimal. Two prose sites quoted the imputation cell as
$0.993$ and now read $0.992$.

The 23-cell partial from the job that died (`sweep_42093.trevally.csv`) was not merged and is kept
as the record of that run. The 10-cell file remains at `sweep_42093.10cells.csv` as the amendment
requires.

## Correction to the 05:30 amendment: the surrogate null is ANTI-conservative on 8 of 17 (2026-09-09 13:10)

The amendment of 2026-09-04 05:30 substituted, for the cross-validated hierarchy's permuted-mask
control, **the larger of the two fitting rules' null gains** — on the argument that on a permuted
mask the inner CV would take whichever rule looks better, making the substitution conservative.
That argument was never checked. `prereg/SWEEPNULL.md` checked it by fitting `family_cv` itself on
a permuted mask, five permutation seeds per cell, on seeds 0–1 of all 17 datasets (85 jobs, all
landed, none dropped). Its prediction **P2 — that the surrogate is at least the true null on at
least 12 of 17 — FAILS at 9 of 17.**

**The substitution is conservative on 9 and anti-conservative on 8.** Named, as registered, with
the direction per dataset (`results/sweepnull_summary.csv`, committed; `conservative=1` means the
surrogate sits at or above the true `family_cv` null and the published excess is understated):

- **Anti-conservative — the published excess is OPTIMISTIC** (8): `cand_airbnb`,
  `cand_mimic4_regime`, `cand_nhanes`, `sweep_42093`, `sweep_42737`, `sweep_42739`,
  `sweep_46654`, `sweep_46703`.
- **Conservative, as the amendment assumed** (9): `cand_acs_income`, `cand_eicu_regime`,
  `cand_higgs`, `cand_porto`, `sweep_41275`, `sweep_42080`, `sweep_42136`, `sweep_42333`,
  `sweep_46725`.

**How much optimism.** The largest inflation of any published excess is **+0.0086**, on
`cand_nhanes`; it is the largest both among the nine wins and over all seventeen datasets. NHANES'
excess against the true null is still **+0.0133**, well clear of the $+0.002$ floor.

**No published win depends on the substitution.** SWEEPNULL's P1 — that at least 7 of the 9 CV
wins still clear $+0.002$ against the real `family_cv` null — **holds at 9 of 9**. The sweep table,
`tables/sweep_counts.tex` and `\SweepWinTotal` are therefore NOT regenerated: the corrected
criterion returns the same nine wins.

**Nor did the substitution hide a win.** Checked rather than assumed, because the conservative
direction on the other nine datasets could in principle have suppressed a true win: for every one
of the eight non-wins the binding failure is the **median gain or the p-value, not the excess**, so
no non-win becomes a win under the true null. (`cand_mimic4_regime` is the one to watch: on seeds
0–1 its surrogate excess clears the floor while its true excess is $-0.0025$, so the real null
removes a would-be win rather than adding one. The published table scores it "no" on all its seeds
regardless.)

**What this changes in the paper.** The claim that the substitution is conservative is withdrawn
and replaced by the measurement. `tables/sweep.tex`'s caption no longer says the CV hierarchy has
no permuted run of its own — it now has one, on seeds 0–1.
