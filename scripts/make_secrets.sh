#!/usr/bin/env bash
# Generate random S3 credentials locally (git-ignored) and create the Kubernetes Secrets.
set -euo pipefail
mkdir -p .secrets
if [ ! -f .secrets/s3.env ]; then
  AK="AK$(openssl rand -hex 8)"; SK="$(openssl rand -hex 20)"
  printf 'export AWS_ACCESS_KEY_ID=%s\nexport AWS_SECRET_ACCESS_KEY=%s\nexport S3_ENDPOINT=http://localhost:8333\n' "$AK" "$SK" > .secrets/s3.env
  chmod 600 .secrets/s3.env
fi
# shellcheck disable=SC1091
source .secrets/s3.env
for ns in app pipeline; do
  kubectl -n "$ns" create secret generic s3-credentials \
    --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" --dry-run=client -o yaml | kubectl apply -f -
done
cat > .secrets/s3.json <<JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$AWS_ACCESS_KEY_ID","secretKey":"$AWS_SECRET_ACCESS_KEY"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweedfs-s3-config --from-file=s3.json=.secrets/s3.json \
  --dry-run=client -o yaml | kubectl apply -f -
