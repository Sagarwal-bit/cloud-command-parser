# Cloud Command Parser: knowledge distillation and deployment on a local Kubernetes cloud

Student: **Vivek Sagarwal** · Roll number: **230101055** · GitHub: [Sagarwal-bit](https://github.com/Sagarwal-bit)
Repository: **https://github.com/Sagarwal-bit/cloud-command-parser** (intended URL; existence on GitHub not yet verified, see STATUS.md)
Release (model weights): **https://github.com/Sagarwal-bit/cloud-command-parser/releases/tag/model-release**

> **Status:** see `STATUS.md` for what is implemented, what was executed and what is still pending.
> Anything marked *PENDING* has not been run yet; no result in this repository is invented.

## What it does
A small voice-assistant style parser: one English command in, one JSON object out
(`intent`, `date`, `time`, `place`). The teacher (Phi-3.5-mini via Ollama, temperature 0, seed 42)
labels 3,000 SLURP commands in parallel workers; Pythia-70M is fine-tuned on those replies
(sequence-level distillation, CPU only) and served by a FastAPI container on k3d/Kubernetes.

## Architecture
```
commands_pool.jsonl --> SeaweedFS (datasets) --> 2 worker Pods (pipeline ns) --> Ollama phi3.5 (laptop)
                                   shard-0/1.jsonl --> worker/clean.py --> datasets/v1/train.jsonl (+sha256)
train.jsonl --> training/train.py (CPU) --> SeaweedFS (models/v1, models/v2) + GitHub Release assets
client --> Traefik Ingress :8080 --> Service --> Deployment (2 Pods, HPA 1-2) --> model from SeaweedFS at start-up
```
Namespaces: `data` (SeaweedFS), `pipeline` (labelling workers), `app` (service).

## Technologies
k3d/k3s, Kubernetes, SeaweedFS (S3 API), Ollama + phi3.5, PyTorch (CPU), Hugging Face Transformers,
FastAPI/uvicorn, Docker, Locust, GitHub Actions, gitleaks, ruff, pytest.

## Repository structure
`cluster/` k3d config · `k8s/` manifests · `worker/` sharded labelling + `clean.py` · `training/` config, trainer,
loss.csv · `service/` API · `tests/` · `scripts/` helpers · `network/` subnets + NACL · `data/`, `tools/` (provided kit,
unchanged) · `prompts/` teacher prompt · `results/` evidence · `models/vN/model.sha256` · `report/` · `reflection/`.

## Prerequisites
Docker, k3d ≥ 5, kubectl, Python 3.11, make, curl, [Ollama](https://ollama.com) with `ollama pull phi3.5`
(only for re-labelling), `pip install locust` (load test). Roughly 8 GB RAM free.

## Quick start (fresh clone, 2 commands)
```bash
git clone https://github.com/Sagarwal-bit/cloud-command-parser cloud-command-parser && cd cloud-command-parser
make up        # cluster, SeaweedFS, images, buckets, models from the Release, deployment
curl -s -X POST localhost:8080/parse -H 'Content-Type: application/json' -d '{"text":"what is the weather in london"}'
```
`make up` does **not** repeat the multi-hour teacher labelling; it uses `data/train.jsonl` and the Release models.
Override the Release location with `REPO_SLUG=<user>/<repo> RELEASE_TAG=model-release make up`.

## Task 1: teacher labelling (run once, takes hours)
```bash
OLLAMA_HOST=0.0.0.0 ollama serve &            # laptop; Pods reach it at host.k3d.internal:11434
ollama pull phi3.5
kubectl apply -f k8s/worker-job.yaml           # 2 workers, SHARD_INDEX 0 and 1, namespace pipeline
kubectl -n pipeline logs -f -l job-name=teacher-labelling --prefix
kubectl -n data port-forward svc/seaweedfs 8333:8333 &  &&  source .secrets/s3.env
python -m worker.clean                          # -> datasets/v1/train.jsonl, train.sha256, data/clean_stats.json
python scripts/storage.py get datasets v1/train.jsonl data/train.jsonl
```
Teacher settings: `temperature 0`, `seed 42`, JSON mode (`format: json`). Prompt: `prompts/teacher_prompt.txt`.

## Task 2: training
```bash
pip install -r service/requirements.txt pyyaml==6.0.2
make train SUBSET=50          # smoke test (writes training/loss_subset.csv)
make train VERSION=v1         # full run, reads only training/config.yaml; writes training/loss.csv, model_out/v1/
make train VERSION=v2
python scripts/storage.py put-dir model_out/v1 models models/v1     # object storage
gh release create model-release model_out/model-v1.tar.gz model_out/model-v2.tar.gz   # GitHub Release assets
```
`models/vN/model.sha256` = SHA-256 of the Release archive `model-vN.tar.gz` (deterministic tar.gz).
Evaluation of teacher / untrained Pythia / student:
```bash
python scripts/evaluate.py teacher --out results/teacher_predictions.jsonl     # needs Ollama
python scripts/evaluate.py model --model EleutherAI/pythia-70m --out results/baseline_predictions.jsonl
python scripts/evaluate.py model --model model_out/v1 --out results/student_predictions.jsonl
```

## Task 3: container
```bash
docker build -t command-parser:1.0 .                 # one command, pinned dependencies, no weights
docker images command-parser:1.0                     # size must be <= 2 GB
kubectl -n data port-forward --address 0.0.0.0 svc/seaweedfs 8333:8333 &
bash scripts/container_limits_test.sh                # 50 sequential requests at 1 CPU / 1 GiB, peak memory
```
Environment variables: `MODEL_URI`, `MODEL_VERSION`, `S3_ENDPOINT`, `MAX_NEW_TOKENS`, `FAULT_INJECT` (=1 forces `not json`).
Credentials come only from the Kubernetes Secret `s3-credentials` (generated at deploy time, never committed).

## Task 4 and 7: Kubernetes experiments and load test
```bash
bash scripts/loadtest.sh 2m results/loadtest/loadtest        # standard Locust command
kubectl -n app set env deployment/command-parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2/   # rolling update (run with a longer load test)
kubectl -n app rollout undo deployment/command-parser        # rollback
kubectl -n app delete pod <one-pod>                           # recovery
bash scripts/coldstart.sh                                     # 3 cold starts + median
python scripts/cost.py --replicas 2 --stats results/loadtest/loadtest_stats.csv
```
For the load-balancing run, scale to exactly two Ready replicas first (`kubectl -n app delete hpa command-parser`
or `kubectl -n app scale deployment command-parser --replicas=2`, then re-apply `k8s/hpa.yaml`).

## Task 5: network
`network/subnets.md`, `network/nacl.json`. Check: `python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check` (6/6).

## Tests and CI
`make lint`, `make test`. `.github/workflows/ci.yml`: gitleaks → lint → unit tests → model evaluation (Release asset) → quality gate
(`score.py --min-validity 95`). Run the workflow manually with *use_untrained_baseline = true* to show the gate failing.

## Shutdown
`make down` (deletes the k3d cluster). `rm -rf .secrets model_out` removes local credentials and weights.

## Object storage
SeaweedFS S3 API, `data` namespace, port 8333. Buckets `datasets` (`commands_pool.jsonl`, `teacher/shard-N.jsonl`,
`v1/train.jsonl`, `v1/train.sha256`) and `models` (`v1/…`, `v2/…`).

## Network configuration
10.20.0.0/16 → app 10.20.0.0/22, public 10.20.4.0/24, data 10.20.5.0/25, management 10.20.5.128/27. NACL for the public subnet in `network/nacl.json`.

## Results and limitations
Measured results are in `results/` and in `report/report.pdf` (see `STATUS.md` for which are still pending).
Limitations: single-node k3d (no multi-machine fault tolerance), 70M-parameter student with a CPU-only budget, labels
are the teacher's (errors are inherited), the HPA cannot show real scale-out capacity on one laptop.
