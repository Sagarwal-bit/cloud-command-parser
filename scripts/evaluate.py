"""Produce raw predictions on data/validation.jsonl, then score them with tools/score.py.

  python scripts/evaluate.py teacher  --out results/teacher_predictions.jsonl
  python scripts/evaluate.py model    --model PATH_OR_HF_ID --out results/student_predictions.jsonl
  python scripts/evaluate.py service  --url http://localhost:8080 --out results/service_predictions.jsonl

`model` with --model EleutherAI/pythia-70m evaluates the original, untrained baseline.
Predictions are the raw model text, unedited. Reports are written next to the predictions.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from service.parsing import build_prompt, extract_output  # noqa: E402
from worker.worker import ask_teacher  # noqa: E402


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def predict_teacher(rows, a):
    prompt = open(a.prompt, encoding="utf-8").read().strip()
    return [ask_teacher(r["text"], prompt, a.ollama, "phi3.5") for r in rows]


def predict_model(rows, a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "4")))
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model).eval()
    outs = []
    for r in rows:
        enc = tok(build_prompt(r["text"]), return_tensors="pt")
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=a.max_new_tokens, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        outs.append(extract_output(tok.decode(gen[0][enc["input_ids"].shape[1]:],
                                              skip_special_tokens=True)))
    return outs


def predict_service(rows, a):
    outs = []
    for r in rows:
        req = urllib.request.Request(a.url.rstrip("/") + "/parse",
                                     data=json.dumps({"text": r["text"]}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                outs.append(resp.read().decode())
        except Exception as exc:  # HTTP 500 etc. counts as an invalid prediction
            outs.append(f"HTTP_ERROR {exc}")
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["teacher", "model", "service"])
    ap.add_argument("--gold", default="data/validation.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--prompt", default="prompts/teacher_prompt.txt")
    ap.add_argument("--url", default="http://localhost:8080")
    a = ap.parse_args()
    rows = read(a.gold)
    preds = {"teacher": predict_teacher, "model": predict_model, "service": predict_service}[a.mode](rows, a)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r, p in zip(rows, preds):
            f.write(json.dumps({"id": r["id"], "prediction": p}, ensure_ascii=False) + "\n")
    report = a.out.replace("_predictions.jsonl", "_validation.json")
    subprocess.run([sys.executable, "tools/score.py", a.out, a.gold, "--out", report], check=True)


if __name__ == "__main__":
    main()
