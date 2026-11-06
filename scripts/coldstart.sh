#!/usr/bin/env bash
# Task 4.7: delete all Pods three times; time Pod creation -> Ready; print the median.
set -euo pipefail
OUT=results/command_outputs/coldstart.txt; : > "$OUT"
for run in 1 2 3; do
  kubectl -n app delete pod -l app=command-parser --wait=true >/dev/null
  sleep 3
  kubectl -n app wait --for=condition=Ready pod -l app=command-parser --timeout=600s >/dev/null
  kubectl -n app get pods -l app=command-parser -o json | python3 -c '
import json,sys,datetime as d
p=lambda s:d.datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ")
for pod in json.load(sys.stdin)["items"]:
    ready=[c for c in pod["status"]["conditions"] if c["type"]=="Ready"][0]["lastTransitionTime"]
    print((p(ready)-p(pod["metadata"]["creationTimestamp"])).total_seconds())' | tee -a "$OUT"
done
kubectl -n app logs -l app=command-parser --tail=5 | tee results/logs/coldstart_model_download.log
python3 - <<PY | tee -a "$OUT"
import statistics
v=[float(x) for x in open("$OUT").read().split()]
print("median_seconds", statistics.median(v), "(over", len(v), "Pod start-ups; 2 Pods x 3 runs)")
PY
