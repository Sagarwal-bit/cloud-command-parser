#!/usr/bin/env bash
# Standard assignment load test (Task 7 / Task 4.8). Usage: scripts/loadtest.sh [run-time] [csv-prefix]
set -euo pipefail
RT="${1:-2m}"; PFX="${2:-results/loadtest/loadtest}"
mkdir -p "$(dirname "$PFX")"
LOADTEST_HEADERS_OUT="${PFX}_headers.json" \
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time "$RT" \
  --host http://localhost:8080 --csv "$PFX" || true   # Locust exits 1 on any failure; read the numbers
