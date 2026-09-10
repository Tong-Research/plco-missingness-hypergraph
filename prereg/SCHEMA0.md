# SCHEMA0: is the ICU site x variable incidence a non-trivial hypergraph? (pre-registered 2026-09-06 15:05)

Step 0 of `papers/SCHEMA-HYPERGRAPH-PRIOR-ART.md` §8. The identification half of the schema-hypergraph idea is
vacuous on a database whose site x variable incidence has a complete, chordal 2-section and an alpha-acyclic hypergraph.

## Design (`experiments/probe_schema0.py`)
eicu_sites (100 hospitals x 42 variables) and mimic4_sites (9 units x 42 variables). A variable is present at a site if
observed in >= t of that site's rows, t in {0.01, 0.05, 0.20}. Report distinct hyperedges, 2-section completeness,
pair coverage c_ij, chordality, alpha-acyclicity (GYO), components.

## Predictions (the agent's expectation, registered as such)
P1. eICU: the 2-section is complete at t = 0.05 (every variable pair co-recorded at some hospital).
P2. eICU: the hypergraph is alpha-acyclic at every threshold.
P3. eICU: minimum pair coverage c_ij >= 5 hospitals at t = 0.05.

## Withdrawal / continuation
If P1-P3 hold -> identification is vacuous on the data this project holds; the schema-hypergraph direction is closed
here (YAIB's five databases are not on the fleet and are out of scope). If P1 fails (some pair is never co-recorded)
or P2 fails (a cycle exists) -> step 0 passes and the T1/T2 tests of §8 are worth pre-registering separately.

## Outcome (2026-09-06 15:25; scorer `experiments/score_round6.py`)

P1, P2, P3 all HOLD on eICU at every threshold: the 2-section is complete (no variable pair is unrecorded everywhere),
the hypergraph is alpha-acyclic and chordal, and the least-covered pair is still recorded at 61 of 100 hospitals at
t = 0.05 (43 at t = 0.20). MIMIC-IV's nine units are a single full hyperedge at t = 0.01. Identification is vacuous on
every multi-site matrix this project holds; the schema-hypergraph direction is closed here.
Disclosure: the script was smoke-tested on mimic4_sites on dugong after the freeze and before the farm run.

Scorer output, verbatim:

```
=== SCHEMA0 ===
P1 eICU 2-section complete at 0.05: HOLDS   P2 acyclic at every threshold: HOLDS   P3 min pair coverage at 0.05 = 61 (>= 5): HOLDS
                        sites  variables  distinct_edges  full_edges  complete_2section  pairs_zero  pairs_le1  min_cov  median_cov  chordal  components  acyclic  min_edge_size  median_edge_size
dataset      threshold                                                                                                                                                                            
eicu_sites   0.01         100         42              25          46                  1           0          0       63        97.0        1           1        1             34              41.0
             0.05         100         42              32          42                  1           0          0       61        95.0        1           1        1             34              41.0
             0.20         100         42              67          15                  1           0          0       43        86.0        1           1        1             25              40.0
mimic4_sites 0.01           9         42               1           9                  1           0          0        9         9.0        1           1        1             42              42.0
             0.05           9         42               3           7                  1           0          0        7         9.0        1           1        1             39              42.0
             0.20           9         42               6           1                  1           0          2        1         9.0        1           1        1             32              40.0
```
