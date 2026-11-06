# Reflection: handwritten-ready draft (max 3 pages, write in your own words)

**Do not submit this typed text. Handwrite it, scan it, and name the file `230101055.pdf` exactly.**
Header on page 1: Name: Vivek Sagarwal · Roll number: 230101055 · GitHub: https://github.com/Sagarwal-bit/cloud-command-parser

Fill the **[bracketed]** parts from your real runs. Delete anything that did not happen to you.

## Page 1: what I learned and Tasks 1 to 2
- Knowledge distillation: a small student copies a teacher. I used sequence-level KD, where the student trains on the
  teacher's generated JSON, not on its logits. [one sentence in your own words on why logits were not available:
  the teacher runs through Ollama, which returns text, and phi3.5 and Pythia use different tokenizers.]
- Task 1: I learned how to run SeaweedFS in k3d, and how sharding by `line_number % SHARD_COUNT` lets two workers run
  without overlap. Labelling took [X hours]. Challenge: [e.g. Ollama not reachable from the Pods → used
  host.k3d.internal and OLLAMA_HOST=0.0.0.0]. The cleaning step kept [N] of 3000 records; the biggest rejection reason was [a/b/c/d/dup].
- Task 2: fine-tuning Pythia-70M on CPU took [X minutes]. Final loss [value]. Student full-frame [x%] vs teacher [y%].
  What surprised me: [your observation]. Limitation: the student copies the teacher's mistakes.

## Page 2: Tasks 3 to 5
- Task 3: the service downloads the model at start-up; /readyz is 503 until it is loaded. Image size [X MB]; peak memory
  [X MiB] at 1 CPU / 1 GiB. Problem I hit: [e.g. default torch wheel made the image huge → CPU-only wheel].
- Task 4: rolling update with maxUnavailable 0 gave [x%] failures; rollback returned X-Model-Version v1. Cold start
  median [X s]. Honest limitation: one node, so no real fault tolerance; the HPA only shows policy, not real capacity.
- Task 5: I split 10.20.0.0/16 into /22, /24, /25, /27 (largest first). A stateless NACL needs separate reply rules
  for ephemeral ports 1024-65535, and the deny for 198.51.100.0/24 must have a lower rule number than the allow rules.

## Page 3: Tasks 6 to 7, challenges, improvements
- Task 6: CI order is gitleaks, lint, tests, evaluation from the Release, gate. The failed run with the untrained model: [link].
- Task 7: p50 [ms], p95 [ms], [rps] req/s, error rate [x%]. Cost per 1000 requests [value INR]. SLO [target], budget used [x%].
- AI use: I used Claude for scaffolding and checked it by [what you did]. Things it got wrong that I fixed: [list].
- What I would improve: [e.g. logit-based distillation, quantisation, a multi-node cluster, a larger student, better prompt].

## Scanning checklist
- [ ] Handwritten on paper, max 3 pages, name + roll number + GitHub link on page 1
- [ ] Scan at readable resolution (≥150 dpi), single PDF, pages in order
- [ ] File named exactly `230101055.pdf` (no spaces, no extra text)
- [ ] Put it at the top level of `230101055.zip` next to the repo contents
