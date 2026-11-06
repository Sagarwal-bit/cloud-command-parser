"""Sharded teacher-labelling worker.

Env: SHARD_INDEX (from 0), SHARD_COUNT, S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
     OLLAMA_URL (default http://host.k3d.internal:11434), TEACHER_MODEL (default phi3.5),
     PROMPT_FILE (default /app/prompts/teacher_prompt.txt)

Line n (counting from 0) of commands_pool.jsonl belongs to shard n % SHARD_COUNT. The worker sends
each of its commands to the teacher (temperature 0, seed 42) and writes, per command,
{"id", "text", "teacher_raw"} where teacher_raw is the teacher's exact reply, to
datasets/teacher/shard-<SHARD_INDEX>.jsonl.  It resumes from an existing shard object.
"""
import json
import os
import sys
import time
import urllib.request

TEACHER_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 128}


def select_shard(lines, shard_index, shard_count):
    """Return the non-empty lines whose 0-based line number % shard_count == shard_index."""
    if not 0 <= shard_index < shard_count:
        raise ValueError("SHARD_INDEX must satisfy 0 <= SHARD_INDEX < SHARD_COUNT")
    return [ln for n, ln in enumerate(lines) if n % shard_count == shard_index]


def ask_teacher(command, system_prompt, url, model, retries=5):
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",  # Ollama JSON mode: constrains decoding to syntactically valid JSON
        "options": TEACHER_OPTIONS,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": command}],
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.load(resp)["message"]["content"]
        except Exception as exc:
            print(f"teacher call failed ({exc!r}), retry {attempt + 1}/{retries}", flush=True)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"teacher unreachable for command {command!r}")


def s3_client():
    import boto3
    return boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="us-east-1")


def read_object_lines(s3, bucket, key):
    try:
        return s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8").splitlines()
    except s3.exceptions.NoSuchKey:
        return []


def main():
    idx, count = int(os.environ["SHARD_INDEX"]), int(os.environ["SHARD_COUNT"])
    url = os.environ.get("OLLAMA_URL", "http://host.k3d.internal:11434")
    model = os.environ.get("TEACHER_MODEL", "phi3.5")
    prompt = open(os.environ.get("PROMPT_FILE", "/app/prompts/teacher_prompt.txt"),
                  encoding="utf-8").read().strip()
    s3 = s3_client()
    key = f"teacher/shard-{idx}.jsonl"
    commands = select_shard(read_object_lines(s3, "datasets", "commands_pool.jsonl"), idx, count)
    done = {json.loads(ln)["id"]: ln for ln in read_object_lines(s3, "datasets", key) if ln.strip()}
    print(f"shard {idx}/{count}: {len(commands)} commands, {len(done)} already done", flush=True)
    out = list(done.values())
    for n, line in enumerate(commands, 1):
        rec = json.loads(line)
        if rec["id"] in done:
            continue
        raw = ask_teacher(rec["text"], prompt, url, model)
        out.append(json.dumps({"id": rec["id"], "text": rec["text"], "teacher_raw": raw},
                              ensure_ascii=False))
        if n % 25 == 0 or n == len(commands):
            s3.put_object(Bucket="datasets", Key=key, Body=("\n".join(out) + "\n").encode())
            print(f"shard {idx}: {n}/{len(commands)} uploaded", flush=True)
    s3.put_object(Bucket="datasets", Key=key, Body=("\n".join(out) + "\n").encode())
    print(f"shard {idx} finished: {len(out)} records", flush=True)


if __name__ == "__main__":
    sys.exit(main())
