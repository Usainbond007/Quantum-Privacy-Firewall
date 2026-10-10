#!/usr/bin/env bash
# Resumable end-to-end driver: dataset -> benchmark -> defense. Safe to re-run after any interruption.
set -euo pipefail; cd "$(dirname "$0")"; P=${1:-full}; W=${2:-2}
python3 build_paper_dataset.py --profile "$P" --workers "$W"
python3 run_paper_benchmark.py --profile "$P" > ../logs/bench_$P.log 2>&1 &
BP=$!
python3 run_paper_defense.py --profile "$P" --workers 1 > ../logs/defense_$P.log 2>&1 &
DP=$!
wait $BP; wait $DP
