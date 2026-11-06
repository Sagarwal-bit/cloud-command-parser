"""Sequence-level distillation: fine-tune Pythia-70M on the teacher's JSON replies (CPU).

  python -m training.train [--version v1] [--subset N]
Reads training/config.yaml only.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import random
import sys
import tarfile
import time

import yaml

from service.parsing import build_prompt, build_training_text, canonical_target


def load_examples(path, limit):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def write_loss(path, version, rows):
    """Keep one row per (version, epoch); rewrite the rows of this version only."""
    existing = []
    if os.path.exists(path):
        with open(path, newline="") as f:
            existing = [r for r in csv.DictReader(f) if r["version"] != version]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["version", "epoch", "train_loss"])
        for r in existing:
            w.writerow([r["version"], r["epoch"], r["train_loss"]])
        for epoch, loss in rows:
            w.writerow([version, epoch, f"{loss:.6f}"])


def package_dir(model_dir, version):
    """Deterministic tar.gz of the model dir; returns (archive path, sha256 of the archive)."""
    archive = os.path.join(os.path.dirname(model_dir), f"model-{version}.tar.gz")
    names = sorted(n for n in os.listdir(model_dir) if not n.endswith(".sha256"))
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for n in names:
            info = tar.gettarinfo(os.path.join(model_dir, n), arcname=n)
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            with open(os.path.join(model_dir, n), "rb") as fh:
                tar.addfile(info, fh)
    import gzip
    with open(archive, "wb") as out, gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    digest = hashlib.sha256(open(archive, "rb").read()).hexdigest()
    return archive, digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--subset", type=int, default=0)
    ap.add_argument("--config", default="training/config.yaml")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    vcfg = cfg["versions"][a.version]

    import numpy as np
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    want = cfg["library_versions"]
    for name, mod in (("torch", torch), ("transformers", transformers), ("numpy", np)):
        if not mod.__version__.startswith(str(want[name])):
            print(f"WARNING: {name} {mod.__version__} != configured {want[name]}", file=sys.stderr)

    seed = vcfg["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(cfg["threads"])

    limit = a.subset or cfg["max_records"]
    limit = min(limit, cfg["max_records"])
    rows = load_examples(cfg["train_file"], limit)
    print(f"training on {len(rows)} records, version {a.version}, seed {seed}", flush=True)

    tok = AutoTokenizer.from_pretrained(cfg["base_model"])
    tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg["base_model"])

    examples = []
    for r in rows:
        target = canonical_target(r["teacher_raw"])
        prompt_ids = tok(build_prompt(r["text"]))["input_ids"]
        full_ids = tok(build_training_text(r["text"], target))["input_ids"] + [tok.eos_token_id]
        full_ids = full_ids[: cfg["max_seq_length"]]
        labels = list(full_ids)
        if cfg["mask_prompt_in_loss"]:
            labels[: len(prompt_ids)] = [-100] * min(len(prompt_ids), len(labels))
        examples.append((full_ids, labels))

    def batches(order):
        for i in range(0, len(order), cfg["batch_size"]):
            chunk = [examples[j] for j in order[i:i + cfg["batch_size"]]]
            width = max(len(ids) for ids, _ in chunk)
            ids = torch.full((len(chunk), width), tok.pad_token_id)
            lab = torch.full((len(chunk), width), -100)
            att = torch.zeros((len(chunk), width), dtype=torch.long)
            for k, (x, y) in enumerate(chunk):
                ids[k, :len(x)], lab[k, :len(y)], att[k, :len(x)] = (
                    torch.tensor(x), torch.tensor(y), 1)
            yield ids, att, lab

    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])
    gen = random.Random(seed)
    losses = []
    model.train()
    for epoch in range(1, vcfg["epochs"] + 1):
        order = list(range(len(examples)))
        gen.shuffle(order)
        total, n, t0 = 0.0, 0, time.time()
        for ids, att, lab in batches(order):
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            opt.zero_grad()
            total += loss.item()
            n += 1
        losses.append((epoch, total / n))
        print(f"epoch {epoch}/{vcfg['epochs']} loss {total / n:.4f} ({time.time() - t0:.0f}s)",
              flush=True)

    if a.subset:
        write_loss("training/loss_subset.csv", a.version, losses)
        print("SUBSET run finished (model not saved for release).")
        return
    write_loss(cfg["loss_csv"], a.version, losses)

    out = os.path.join(cfg["output_dir"], a.version)
    os.makedirs(out, exist_ok=True)
    model.eval()
    model.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    json.dump({"version": a.version, "base_model": cfg["base_model"], "seed": seed,
               "epochs": vcfg["epochs"], "learning_rate": cfg["learning_rate"],
               "batch_size": cfg["batch_size"], "records": len(rows),
               "final_loss": losses[-1][1], "torch": torch.__version__,
               "transformers": transformers.__version__},
              open(os.path.join(out, "version.json"), "w"), indent=2)
    archive, digest = package_dir(out, a.version)
    with open(os.path.join(out, "model.sha256"), "w") as f:
        f.write(f"{digest}  {os.path.basename(archive)}\n")
    os.makedirs(f"models/{a.version}", exist_ok=True)
    with open(f"models/{a.version}/model.sha256", "w") as f:
        f.write(f"{digest}  {os.path.basename(archive)}\n")
    print(f"saved {out}; release asset {archive}; sha256 {digest}")


if __name__ == "__main__":
    main()
