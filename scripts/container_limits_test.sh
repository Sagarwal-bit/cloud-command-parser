#!/usr/bin/env bash
# Task 3: 50 sequential requests against the container at 1 CPU / 1 GiB; report peak memory.
# Needs SeaweedFS reachable from the container: run `kubectl -n data port-forward --address 0.0.0.0 svc/seaweedfs 8333:8333`.
set -euo pipefail
source .secrets/s3.env
MODEL_URI="${MODEL_URI:-s3://models/v1/}"
docker rm -f parser-test >/dev/null 2>&1 || true
docker run -d --name parser-test --cpus=1 --memory=1g --memory-swap=1g -p 8000:8000 \
  -e MODEL_URI="$MODEL_URI" -e MODEL_VERSION=v1 -e MAX_NEW_TOKENS=64 \
  -e S3_ENDPOINT=http://host.docker.internal:8333 --add-host=host.docker.internal:host-gateway \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY command-parser:1.0
until [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/readyz)" = 200 ]; do sleep 2; done
( while true; do docker stats --no-stream --format '{{.MemUsage}}' parser-test; sleep 0.5; done > results/command_outputs/docker_stats_samples.txt ) &
SAMPLER=$!
mapfile -t TEXTS < <(python3 -c "import json;[print(json.loads(l)['text']) for l in list(open('data/validation.jsonl'))[:50]]")
codes=""
for t in "${TEXTS[@]}"; do
  codes+="$(curl -s -o /dev/null -w '%{http_code} ' -X POST localhost:8000/parse -H 'Content-Type: application/json' -d "{\"text\":\"$t\"}")"
done
kill $SAMPLER || true
echo "$codes" | tr ' ' '\n' | sort | uniq -c | tee results/command_outputs/container_limits_status_codes.txt
echo "OOMKilled: $(docker inspect -f '{{.State.OOMKilled}}' parser-test)" | tee results/command_outputs/container_limits_oom.txt
echo "peak memory sample (MiB, highest in file):"; sort -h results/command_outputs/docker_stats_samples.txt | tail -1
docker rm -f parser-test >/dev/null
