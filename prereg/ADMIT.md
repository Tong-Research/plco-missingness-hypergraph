# ADMIT — is schema complementarity an admission lever, when selection and weighting failed?

**Written 2026-09-08 14:45, BEFORE any measurement.** Runs on committed decision data
(`results/site_rules_*.csv`); no new fitting, no farm job.

## Why this is not C1 again

The complementarity line has three layers and two are closed:

| layer | test | outcome |
|---|---|---|
| **selection** — which partners | C1 (R87) | beats random by 48% with a mirror that loses, then **subsumed by size** |
| **weighting** — how much of each partner | C2 (R88), C4 (R89) | lower ceiling than the scalar blend; inert in the pattern hypergraph |
| **admission** — join at all | **never tested** | — |

C1's kill was specifically *"size subsumes complementarity at selection time"*. At admission the
competing signal is not size but **adequacy**, and R86 measured the two as orthogonal:
rho(schema overlap, EPV) = -0.036, rho(schema overlap, n_target) = -0.024. So the argument that
killed C1 does not carry over, and the question is open on its own terms rather than by hope.

## Design

Per-decision records already committed: `schema_jaccard`, `epv_target`, `benefit`, `helped`.
Complementarity is `1 - schema_jaccard`. The paper's rule is `epv_target < EPV_CUT`.

Two rules compared on the same decisions:

- **baseline** — admit iff `epv < cut` (Paper C's published gate)
- **combined** — admit iff `epv < cut` AND `complementarity >= c`

`cut` is Paper C's published value, not refitted. `c` is chosen on the development collections
only, on a fixed grid of the complementarity deciles, maximising mean benefit over admitted
decisions.

Primary metric: **mean benefit over admitted decisions**. Secondary: fraction helped, and the
number of decisions each rule admits (a rule that improves the mean by admitting almost nobody is
not an improvement; any rule admitting fewer than half the baseline's decisions is reported as
degenerate and does not count as a pass).

## Split, by collection and fixed here

- **Development (choose `c`):** the eICU pools — `hs_eicu_sites`, `eicu_k10`, `eicu_d16`,
  `eicu_d24`, `eicu_d42`, `eicu_longstay`, `hs_eicu_top30`, `top30`, `floor540`, `eicu_only`,
  `10seed`, `multimetric`
- **Holdout (never touched until `c` is fixed):** the MIMIC-only pools —
  `hs_mimic_sites_unit_x_system`, `hs_mimic4_sites`, `mimic_k8`
- **Excluded from both:** `all` and `combined`, which mix eICU with MIMIC. A pool containing
  development sources cannot test transfer, and putting it in the holdout would leak. Reported
  separately as context and not used for any prediction.

`top30` is an eICU carving despite the name not saying so, and sits in development for that
reason. Assigning it to the holdout would have leaked eICU into the transfer test.

Split by collection, not by row: the eICU pools are re-carvings of one hospital corpus and a
row-split would leak. MIMIC-III and MIMIC-IV are genuinely separate sources.

## Predictions

- **P1.** On development, the combined rule raises mean benefit over admitted decisions by
  >= +0.002 against the baseline, without falling below half its admitted count.
- **P2.** That improvement transfers: >= +0.002 on at least one of the two MIMIC holdout
  collections, and not worse than -0.002 on either.
- **P3 (the null).** No improvement >= +0.002 on either MIMIC holdout.

R86 found the overlap-benefit gradient **reverses on MIMIC-IV**, the harmful pool, so P2 is a
genuinely hard test and P3 is a live possibility. That is stated here rather than discovered later.

## Withdrawal and reporting

- If **P1 fails**, complementarity is not an admission lever even where it was measured to
  predict benefit, and the line closes at all three layers.
- If **P1 holds and P2 fails**, the signal is real and regime-bound: it does not transfer from
  eICU to MIMIC. That is Paper C's regime thesis at a third layer and is reported as such — it is
  **not** rescued by refitting `c` on the holdout.
- If **P1 and P2 hold**, complementarity is an admission lever, which contradicts the current
  closing sentence of the complementarity line and that sentence is rewritten.
- The admitted-count is reported for every rule, always, so a rule that "wins" by admitting
  almost nobody is visible.
