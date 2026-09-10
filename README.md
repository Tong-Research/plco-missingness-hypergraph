# Shrinkage on the Missingness Hypergraph

Code, pre-registrations and aggregate results for the article of the same title
(Vivatchai Kaveeta, Prompong Sugunnasil, Juggapong Natwichai, Chiang Mai University). Generated from the authors' research monorepo at
commit `d6a46e4` on 2026-09-10 by `build_release.py`; the generator's verification step imported the
library and regenerated the tables and figures in this tree.

## Layout
- `src/hgmiss/` — the library (estimators, baselines, protocol, metrics, data loaders).
- `experiments/` — every experiment script the article uses, and the queue tooling the runs were made with.
- `figures/` — the figure and table generators (run from inside `figures/`) and their aggregate inputs.
- `results/` — aggregate outputs (per seed and fold, or per decision for public collections) that the tables are built from; files over 1 MB are gzip-compressed and `reproduce.sh` inflates them.
- `prereg/` — the pre-registrations (predictions and withdrawal conditions written before each run).

## What is not here
The manuscript source is not included: this repository carries the code, the
pre-registrations and the aggregate results only. `reproduce.sh` regenerates the tables and
figures from `results/`.

## Reproduce the tables and figures from the shipped results
```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && pip install -e .
./reproduce.sh
```

## Re-run the experiments
PLCO: apply at https://cdas.cancer.gov/plco/ and place the CDAS export under datasets/plco/ (see src/hgmiss/data/plco.py for the expected files). MIMIC-IV: PhysioNet credentialed access; build the matrix with experiments/mimic4_sites.py. The eleven public datasets are fetched from OpenML by experiments/run_real_suite.py.
Set `PLCO_ROOT` to the PLCO directory where applicable. Runs are launched through `experiments/spinner_runner.py`
(a queue runner) or directly, e.g. `python experiments/run_h1_h4.py --cohort lung`.

## Data not included
Nothing was withheld; every result file the scripts reference is included.

## Licence
MIT (see LICENSE). Please cite the article (CITATION.cff).
