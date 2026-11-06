# AI use declaration

> Draft prepared with the AI assistant. **Vivek: read it, correct anything that is not true for you, and
> keep it honest before submitting.**

## Tools
- **Claude (Anthropic)**, chat interface: used to read the assignment, scaffold the repository (service, worker,
  cleaning, training script, Kubernetes manifests, scripts, CI workflow, tests), compute the Task 5 subnet table and
  NACL, and draft the README, report skeleton and reflection outline.
- (Add any other tool you really used, e.g. GitHub Copilot, ChatGPT, here. Remove this line if none.)

## What the AI did not do
- It did not run the teacher, training, Docker, Kubernetes or Locust steps: those need my laptop. Every number in
  `results/` and the report must come from my own runs.
- It did not write the handwritten reflection.

## How I checked the output
- Ran `python -m pytest` and the provided `tools/nacl_sim.py --check` and `tools/score.py` myself.
- Read the code, ran `make train SUBSET=50`, built the image, and compared behaviour with the assignment text
  (endpoints, headers, error body, `FAULT_INJECT`, NACL rule order).
- Recomputed the subnet table by hand: 2^10-2=1022 ≥ 1000 → /22, 2^8-2=254 → /24, 2^7-2=126 → /25, 2^5-2=30 → /27.
- Did not trust any metric that I did not produce myself; scanned the repo with gitleaks (CI) for secrets.
- (Add what you actually verified and what AI suggestions you rejected or fixed.)
