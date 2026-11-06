"""Command-parser inference service.

Environment: MODEL_URI, MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS (+ FAULT_INJECT for testing).
"""
import os
import threading

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .validator import InvalidModelOutput, validate_output

app = FastAPI(title="command-parser")
state = {"generator": None, "ready": False, "error": None}


class ParseRequest(BaseModel):
    text: str


def _headers():
    return {
        "X-Model-Version": os.environ.get("MODEL_VERSION", "unknown"),
        "X-Served-By": os.environ.get("HOSTNAME", "unknown"),  # Kubernetes sets HOSTNAME = Pod name
    }


def _load():
    try:
        from .model_loader import Generator, download_prefix

        path = download_prefix(os.environ["MODEL_URI"], os.environ["S3_ENDPOINT"], "/tmp/model")
        state["generator"] = Generator(path, int(os.environ.get("MAX_NEW_TOKENS", "64")))
        state["ready"] = True
        print("model loaded; service ready", flush=True)
    except Exception as exc:  # keep the process alive so /healthz stays 200 and logs show why
        state["error"] = repr(exc)
        print(f"model load failed: {exc!r}", flush=True)


@app.on_event("startup")
def startup():
    if os.environ.get("SKIP_MODEL_LOAD") != "1":
        threading.Thread(target=_load, daemon=True).start()


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if state["ready"]:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


@app.post("/parse")
def parse(req: ParseRequest):
    if not state["ready"]:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=_headers())
    raw = state["generator"](req.text)
    if os.environ.get("FAULT_INJECT") == "1":
        raw = "not json"
    try:
        result = validate_output(raw)
    except InvalidModelOutput:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=_headers())
    return JSONResponse(result, status_code=200, headers=_headers())
