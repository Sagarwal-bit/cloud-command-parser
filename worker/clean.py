"""Clean the raw teacher replies and write datasets/v1/train.jsonl (+ SHA-256).

Usage
  python -m worker.clean                       # reads datasets/teacher/shard-*.jsonl from S3,
                                               #   writes datasets/v1/train.jsonl, train.sha256
  python -m worker.clean --local DIR --out OUT # offline: DIR/shard-*.jsonl -> OUT/train.jsonl ...

Each record is rejected for the FIRST reason that applies, so
  input = (a) + (b) + (c) + (d) + duplicates + kept.
  (a) reply is not valid JSON            (b) keys are not exactly intent/date/time/place
  (c) intent not one of the eight        (d) a slot is neither null nor a string found in the command
  (e) duplicate command text; the smallest id is kept (records are processed in id order, and
      duplicates are counted among records that passed (a)-(d)).
"""
import argparse
import glob
import hashlib
import json
import os
import sys

KEYS = {"intent", "date", "time", "place"}
INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query", "calendar_remove",
           "weather_query", "datetime_query", "recommendation_events"}


def check_record(rec):
    """Return None if the record is good, else the rejection reason 'a'..'d'."""
    try:
        obj = json.loads(rec["teacher_raw"])
    except (json.JSONDecodeError, TypeError):
        return "a"
    if not isinstance(obj, dict) or set(obj) != KEYS:
        return "b"
    if not isinstance(obj["intent"], str) or obj["intent"] not in INTENTS:
        return "c"
    for slot in ("date", "time", "place"):
        v = obj[slot]
        if v is not None and not (isinstance(v, str) and v in rec["text"]):
            return "d"
    return None


def clean(records):
    """records: list of dicts {id,text,teacher_raw}. Returns (kept_records, stats)."""
    stats = {"input": len(records), "a_invalid_json": 0, "b_bad_keys": 0, "c_bad_intent": 0,
             "d_bad_slot": 0, "duplicates": 0, "kept": 0}
    names = {"a": "a_invalid_json", "b": "b_bad_keys", "c": "c_bad_intent", "d": "d_bad_slot"}
    seen, kept = set(), []
    for rec in sorted(records, key=lambda r: r["id"]):
        reason = check_record(rec)
        if reason:
            stats[names[reason]] += 1
        elif rec["text"] in seen:
            stats["duplicates"] += 1
        else:
            seen.add(rec["text"])
            kept.append(rec)
    stats["kept"] = len(kept)
    assert stats["input"] == sum(v for k, v in stats.items() if k != "input"), "counts do not add up"
    return kept, stats


def serialise(kept):
    return "".join(json.dumps({"id": r["id"], "text": r["text"], "teacher_raw": r["teacher_raw"]},
                              ensure_ascii=False) + "\n" for r in kept).encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="directory with shard-*.jsonl instead of S3")
    ap.add_argument("--out", default="data", help="local output dir (always written)")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()

    records, s3 = [], None
    if a.local:
        for path in sorted(glob.glob(os.path.join(a.local, "shard-*.jsonl"))):
            with open(path, encoding="utf-8") as f:
                records += [json.loads(ln) for ln in f if ln.strip()]
    else:
        import boto3
        s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="us-east-1")
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket="datasets",
                                                                 Prefix="teacher/shard-"):
            for obj in page.get("Contents", []):
                body = s3.get_object(Bucket="datasets", Key=obj["Key"])["Body"].read().decode()
                records += [json.loads(ln) for ln in body.splitlines() if ln.strip()]

    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        sys.exit("shard outputs contain repeated ids")
    kept, stats = clean(records)
    data = serialise(kept)
    digest = hashlib.sha256(data).hexdigest()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "train.jsonl"), "wb") as f:
        f.write(data)
    with open(os.path.join(a.out, "train.sha256"), "w") as f:
        f.write(f"{digest}  train.jsonl\n")
    with open(os.path.join(a.out, "clean_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    if s3 and not a.no_upload:
        s3.put_object(Bucket="datasets", Key="v1/train.jsonl", Body=data)
        s3.put_object(Bucket="datasets", Key="v1/train.sha256",
                      Body=f"{digest}  train.jsonl\n".encode())
    print(json.dumps(stats, indent=2))
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
