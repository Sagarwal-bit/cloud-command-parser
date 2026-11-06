"""Helper for SeaweedFS (S3 API). Credentials/endpoint come from the environment
(`source .secrets/s3.env`, written by scripts/make_secrets.sh); nothing is stored in Git.

  python scripts/storage.py bootstrap              create buckets, upload commands_pool.jsonl
  python scripts/storage.py put LOCAL_FILE BUCKET KEY
  python scripts/storage.py put-dir LOCAL_DIR BUCKET PREFIX   (e.g. model_out/v1 models models/v1)
  python scripts/storage.py get BUCKET KEY LOCAL_FILE
  python scripts/storage.py get-dir BUCKET PREFIX LOCAL_DIR
"""
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def client():
    return boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
                        region_name="us-east-1")


def ensure_bucket(s3, name):
    try:
        s3.create_bucket(Bucket=name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def main(argv):
    s3 = client()
    cmd = argv[1]
    if cmd == "bootstrap":
        for b in ("datasets", "models"):
            ensure_bucket(s3, b)
        s3.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
        print("buckets ready; commands_pool.jsonl uploaded")
    elif cmd == "put":
        s3.upload_file(argv[2], argv[3], argv[4])
    elif cmd == "put-dir":
        src, bucket, prefix = Path(argv[2]), argv[3], argv[4].strip("/")
        for p in sorted(src.rglob("*")):
            if p.is_file():
                s3.upload_file(str(p), bucket, f"{prefix}/{p.relative_to(src)}")
                print("uploaded", f"{bucket}/{prefix}/{p.relative_to(src)}")
    elif cmd == "get":
        s3.download_file(argv[2], argv[3], argv[4])
    elif cmd == "get-dir":
        bucket, prefix, dest = argv[2], argv[3].strip("/") + "/", Path(argv[4])
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            for o in page.get("Contents", []):
                t = dest / o["Key"][len(prefix):]
                t.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(bucket, o["Key"], str(t))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
