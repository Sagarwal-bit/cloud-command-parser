#!/usr/bin/env bash
# Build and deploy the whole system from a fresh clone (called by `make up`).
# Needs: docker, k3d, kubectl, python3, curl. Does NOT run the multi-hour teacher labelling:
# the dataset and models are taken from the repository / the GitHub Release.
set -euo pipefail
REPO_SLUG="${REPO_SLUG:-Sagarwal-bit/cloud-command-parser}"
RELEASE_TAG="${RELEASE_TAG:-model-release}"
cd "$(dirname "$0")/.."

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q boto3==1.35.20 pyyaml==6.0.2
k3d cluster list cmdparser >/dev/null 2>&1 || k3d cluster create --config cluster/k3d.yaml
kubectl apply -f k8s/namespaces.yaml
bash scripts/make_secrets.sh
kubectl apply -f k8s/seaweedfs.yaml
kubectl -n data rollout status statefulset/seaweedfs --timeout=300s

docker build -t command-parser:1.0 .
docker build -t command-parser-worker:1.0 -f Dockerfile.worker .
k3d image import command-parser:1.0 command-parser-worker:1.0 -c cmdparser

# seed object storage through a temporary port-forward
kubectl -n data port-forward svc/seaweedfs 8333:8333 >/dev/null 2>&1 &
PF=$!; trap 'kill $PF 2>/dev/null || true' EXIT; sleep 5
source .secrets/s3.env
.venv/bin/python scripts/storage.py bootstrap
[ -f data/train.jsonl ] && .venv/bin/python scripts/storage.py put data/train.jsonl datasets v1/train.jsonl
mkdir -p model_out
for v in v1 v2; do
  if [ ! -d "model_out/$v" ]; then
    curl -fsSL -o "model_out/model-$v.tar.gz" "https://github.com/$REPO_SLUG/releases/download/$RELEASE_TAG/model-$v.tar.gz"
    mkdir -p "model_out/$v" && tar -xzf "model_out/model-$v.tar.gz" -C "model_out/$v"
  fi
  .venv/bin/python scripts/storage.py put-dir "model_out/$v" models "models/$v"
done
kill $PF; trap - EXIT

kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml
kubectl -n app rollout status deployment/command-parser --timeout=600s
echo "Ready: curl -s -X POST localhost:8080/parse -H 'Content-Type: application/json' -d '{\"text\":\"what is the weather in london\"}'"
