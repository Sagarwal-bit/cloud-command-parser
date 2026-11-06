"""Download a model from S3-compatible storage and wrap it in a text generator."""
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

from .parsing import build_prompt, extract_output

SKIP_SUFFIXES = (".sha256",)


def download_prefix(model_uri, endpoint, dest):
    """Download every object under s3://bucket/prefix/ into `dest`. Credentials come from the
    environment (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY), injected from a Kubernetes Secret."""
    import boto3

    u = urlparse(model_uri)
    bucket, prefix = u.netloc, u.path.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    s3 = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            rel = obj["Key"][len(prefix):]
            if not rel or rel.endswith(SKIP_SUFFIXES):
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, obj["Key"], str(target))
            count += 1
    if count == 0:
        raise RuntimeError(f"no objects found under {model_uri}")
    print(f"downloaded {count} files from {model_uri} to {dest}", flush=True)
    return dest


class Generator:
    """Greedy decoding with a trained Pythia checkpoint."""

    def __init__(self, model_dir, max_new_tokens=64):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "1")))
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(str(model_dir))
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(str(model_dir)).eval()
        self.max_new_tokens = max_new_tokens
        self._lock = threading.Lock()

    def __call__(self, text):
        enc = self.tok(build_prompt(text), return_tensors="pt")
        with self._lock, self.torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                pad_token_id=self.tok.eos_token_id)
        new_tokens = out[0][enc["input_ids"].shape[1]:]
        return extract_output(self.tok.decode(new_tokens, skip_special_tokens=True))
