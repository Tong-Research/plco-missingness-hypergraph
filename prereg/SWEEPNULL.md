# SWEEPNULL — the sweep's wins against a real null for the arm that wins

**Written 2026-09-08 18:10, BEFORE any measurement.**

## The gap, in the project's own words

Paper 3's limitations section says of an earlier version of its own table:

> An earlier version of this table drew a *single* mask permutation per dataset and reported the
> resulting difference. That design cannot show how much of a per-dataset excess is signal. On
> four of the eight datasets it covered, the excess it reported was smaller than one standard
> deviation of the null it was measured against.

`run_candidate.py` draws **one permutation per (seed, fold) cell**. Paper 1's sweep table is
therefore built on the design Paper 3 disowns.

Worse, and separately: the permuted branch skips `family_cv` and `exact_cv` entirely
(`if not permuted:` at both lines). **The cross-validated hierarchy — the arm that carries every
one of the sweep's nine wins — has no permuted run of its own.** Its null is substituted by the
larger of `ours` and `exact_submodels`. The SWEEP amendment of 2026-09-04 05:30 declares the
substitution; nothing has ever checked whether it is conservative.

Result 219 makes this concrete rather than theoretical: at full schema the *published* estimator
already showed permuted gains above +0.002 on 2 of 17 datasets (`cand_nhanes`, `sweep_46654`).
Both are in the sweep.

## Design

`experiments/probe_sweepnull.py`. For each of the 17 sweep and candidate datasets, the same
holdout slice, subsample and folds the published run used, restricted to **seeds 0 and 1 (ten
cells)** for cost. For each cell and each of **five permutation seeds**, the training mask is
row-permuted (`run_candidate.permute_mask`) and two arms are fitted on it:

- `family_cv` — the CV-selected hierarchy, which has never had a permuted run
- `mean_impute` — its paired comparator, as in the real run

Fifty permuted values per dataset, against the one per cell the published table used.

Nothing about the real run changes. The published real-arm numbers are reused as committed.

## The quantity

For each dataset, the excess is `median over cells of (real gain) - (null gain)`, where gain is
`family_cv - mean_impute`. The published table computes it with a single-permutation null and a
surrogate arm. Here it is computed against the distribution of five permutations of the arm
itself, and the spread of that distribution is reported beside it.

## Predictions

- **P1.** For at least 7 of the 9 datasets the published table scores as a CV win, the excess
  against the real `family_cv` null still clears +0.002.
- **P2.** The surrogate null is conservative: `max(null gain of ours, null gain of
  exact_submodels)` is >= the true `family_cv` null gain on at least 12 of 17 datasets. If this
  fails the published table's excesses are optimistic and the direction is stated per dataset.
- **P3.** On at least 12 of 17 datasets the standard deviation of the five permuted gains is
  below +0.002 — that is, one permutation was an adequate estimate after all.

## Withdrawal and reporting

- If **P1 fails**, one or more published sweep wins do not survive a proper null. Every affected
  dataset is named and the sweep table, `tables/sweep_counts.tex` and the abstract's
  `\SweepWinTotal` are regenerated from the corrected criterion. **This is the outcome that most
  improves the paper and it will be reported in full.**
- If **P2 fails**, the surrogate is anti-conservative and the amendment that introduced it is
  corrected in `prereg/SWEEP.md` with the per-dataset direction.
- If **P3 fails**, the single-permutation design is inadequate as Paper 3 argues, and Paper 1
  gains a sentence saying its sweep null is now a distribution.
- If **all three hold**, the published table is vindicated against its sharpest available
  objection, and that is worth a sentence in Paper 1 and a line in Paper 3's related work.

No dataset, arm or threshold is added after the first number exists. The null is estimated on
seeds 0-1 only and every reported excess says so.

## Pre-measurement note, 2026-09-08 18:15

`probe_sweepnull.py` was smoke-tested once on `sweep_41275` at `--max-n 3000 --seeds 1 --folds 2`,
far below the registered design (100,000 records, 2 seeds, 5 folds), purely to confirm the code
path runs. Those numbers are not a registered measurement and are used nowhere.

## Amendment, 2026-09-09 02:30 — checkpointing, and what the scorer must now check

**No prediction, dataset, arm or threshold changes.** P1--P3 and the withdrawal conditions above
stand exactly as written. This amendment records an operational change made *before any SWEEPNULL
number has been scored*, and one new obligation it places on the scorer.

`probe_sweepnull.py` originally wrote its CSV only after the last of the ten cells. Three jobs hit
the eight-hour wall clock: `cand_acs_income-p4` had finished **nine** cells and lost all nine, and
both `cand_eicu_regime-p0` and `-p4` were killed inside their first cell. The probe now banks each
cell as it completes and resumes from what is on disk. A cell counts as done only when both arms
are present, so a resume never inherits a half-measured cell, and the repair pass writes through a
temp file and an atomic replace.

Two consequences for anyone reading the results directory:

1. **A file in `results/sweepnull/` is no longer evidence that its job finished.** A partial file
   is now a normal intermediate state. The scorer must require all ten cells per
   (dataset, perm) file and **name any file that falls short** rather than averaging whatever
   rows it finds. This is the same failure mode as the silent-success audits of 2026-09-08: an
   analysis that cannot run must not report a result. An incomplete run exits 2 so the farm
   files it as unfinished.
2. **The permutation draw is unchanged.** The RNG is seeded per cell from `(perm, seed, fold)`,
   never from a running counter, so a resumed cell draws exactly the permutation it would have
   drawn in one pass. Resumption cannot alter a single reported number.

A separate scheduling defect was found in the same investigation and is *not* part of this
prereg's design: every job reserved one CPU and then let its BLAS spawn a thread per core, so
Dugong ran six jobs at load 38 on sixteen cores. The same `cand_eicu_regime` cell took 19,395s
there against 1,380s on an unloaded Trevally. Thread counts are now bound to the job's reservation
and the 45 unstarted jobs were resubmitted at `cpus: 3`. This changes how fast the cells are
computed and nothing about what is computed: the arms, splits, subsample and permutations are
untouched, and the 31 cells already collected were verified to parse identically under the new
code before anything was resubmitted.
