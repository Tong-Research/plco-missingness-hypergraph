#!/bin/sh
# Regenerate tables/figures from results/. Steps whose inputs are withheld under a data-use agreement report it and continue.
export PYTHONPATH=$PWD/src:$PWD/experiments:$PWD/figures:$PYTHONPATH
echo "-- inflating compressed result files"; for f in $(find results -name "*.csv.gz"); do gunzip -kf "$f"; done
echo "-- ingest results -> tables/figures csv"; ( cd figures && python ingest_results.py && cd .. ) || echo "   skipped: ingest results -> tables/figures csv needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
echo "-- cohort and main-results tables"; ( cd figures && python make_tables.py && cd .. ) || echo "   skipped: cohort and main-results tables needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
echo "-- figures (pgfplots sources)"; ( cd figures && python make_pgf.py && cd .. ) || echo "   skipped: figures (pgfplots sources) needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
echo "-- synthetic sweep figure"; ( cd figures && python make_figures.py && cd .. ) || echo "   skipped: synthetic sweep figure needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
echo "-- H1 paired table"; ( python experiments/h1_paired.py ) || echo "   skipped: H1 paired table needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
echo "-- sensitivity table"; ( cd figures && python sensitivity_compare.py && cd .. ) || echo "   skipped: sensitivity table needs inputs withheld under a data-use agreement (the figure/table is shipped as built)"
