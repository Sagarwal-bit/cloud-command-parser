# Status checklist (updated at hand-over; **tick only after you run it**)

Legend: **V** = implemented and verified here · **I** = implemented, NOT executed (needs your laptop / GitHub) · **P** = pending, no artefact yet

| Task | Item | State | Notes |
|---|---|---|---|
| 1 | `cluster/k3d.yaml`, `k8s/seaweedfs.yaml`, namespaces | I | YAML parses; cluster never created |
| 1 | `prompts/teacher_prompt.txt` | I | not yet run against phi3.5 |
| 1 | `worker/worker.py` sharding logic | V (unit test) | Ollama/S3 paths not executed |
| 1 | `worker/clean.py` | V (unit tests + synthetic run, deterministic hash) | real counts pending |
| 1 | shard outputs, `train.jsonl`, `train.sha256`, counts table | P | needs the hours-long labelling run |
| 2 | `training/config.yaml`, `train.py`, `make train` | I | torch not available in authoring sandbox |
| 2 | `loss.csv`, models v1/v2, checksums, Release assets | P | |
| 2 | teacher / baseline / student scores in `results/` | P | |
| 2 | one-page explanation (seq-level vs logit-based) | V | in `report/report.md` |
| 3 | `service/` API, validator, FAULT_INJECT | I (validator V by unit tests; FastAPI tests skipped here) | run `make test` locally/CI |
| 3 | Dockerfile (pinned), image ≤ 2 GB, 50-request test, peak memory | I / P | image never built |
| 4 | manifests: Deployment, Service, Ingress, HPA, probes | I | `kubectl apply --dry-run` not run |
| 4 | scaling, rolling update, rollback, recovery, cold start, balancing evidence | P | scripts provided |
| 5 | `network/subnets.md`, `network/nacl.json` | **V** | `nacl_sim.py --check` = 6/6 |
| 6 | Makefile (`up`, `down`), CI workflow, gitleaks, unit tests | I (tests V: 11 pass, 4 skipped without FastAPI) | |
| 6 | failed quality-gate run URL | P | run workflow with `use_untrained_baseline=true` |
| 6 | `AI_USE.md` | V (needs your edits) | |
| 7 | Locust results, cost, SLO, review table | P | `scripts/cost.py` ready |
| – | `report/report.pdf` | draft only; measured sections PENDING | |
| – | handwritten reflection scan `<ROLL>.pdf` | P | only you can produce it |
| – | GitHub repository and main branch | V | Repository created; 62 files pushed successfully. Initial commit: d49ad94 |
| – | GitHub Release with model assets | P | Pending trained model files and checksums |
| – | Git tag `final` | P | Create only after all work and submission files are finalized |

## Repository verification (updated 2026-11-06)

- GitHub profile: https://github.com/Sagarwal-bit
- Repository: https://github.com/Sagarwal-bit/cloud-command-parser
- Repository visibility: Public
- Default branch: `main`
- Initial commit: `d49ad94`
- Project files: 62 files successfully pushed to GitHub.
- GitHub Release: Pending.
- Final tag: Pending.
- Model training and deployment experiments: Pending.