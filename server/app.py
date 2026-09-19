#!/usr/bin/env python3
"""
SDOC hackathon inbox + scoring server.

Serves the dataset to participants over HTTP and scores their submissions
against a ground-truth file that is mounted PRIVATELY and never exposed on any
endpoint.

Public (participant) endpoints
    GET  /health                      liveness probe
    GET  /                            API index
    GET  /emails                      list all email records (no labels)
    GET  /emails/{email_id}           one email record
    GET  /attachments/{path}          download an SI/BL attachment
    GET  /sample_submission           the exact output shape to produce
    POST /submit                      score a submission -> scoreboard JSON

Judge-only endpoint (guarded by X-Judge-Token, off unless JUDGE_TOKEN is set)
    GET  /ground_truth                the labels (returns 404 when disabled)

Environment
    DATA_DIR       default /data           (mount data_v2 here, read-only)
    GROUND_TRUTH   default /secrets/ground_truth.json   (private mount)
    REVEAL_GT      "1" to enable /ground_truth (default off)
    JUDGE_TOKEN    if set, /ground_truth requires header X-Judge-Token: <token>
"""
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse, JSONResponse

import scoring

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
INBOX_DIR = DATA_DIR / "inbox"
ATTACH_DIR = DATA_DIR / "attachments"
GROUND_TRUTH_PATH = Path(os.environ.get("GROUND_TRUTH", "/secrets/ground_truth.json"))
SAMPLE_PATH = DATA_DIR / "sample_submission.json"
REVEAL_GT = os.environ.get("REVEAL_GT", "0") == "1"
JUDGE_TOKEN = os.environ.get("JUDGE_TOKEN")

app = FastAPI(title="SDOC Hackathon Inbox", version="2.0",
              description="Serves the shipping-docs inbox and scores submissions. "
                          "Ground truth is held privately and never served.")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _load_inbox():
    """All email records, sorted by id. Labels are NOT here — inbox files only
    contain email_id/from/subject/body/attachments."""
    out = []
    for p in sorted(INBOX_DIR.glob("email_*.json")):
        out.append(json.loads(p.read_text()))
    return out


def _load_ground_truth():
    if not GROUND_TRUTH_PATH.exists():
        raise HTTPException(503, "ground truth not mounted; scoring unavailable")
    return json.loads(GROUND_TRUTH_PATH.read_text())


# --------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok",
            "emails": len(list(INBOX_DIR.glob("email_*.json"))),
            "scoring_available": GROUND_TRUTH_PATH.exists()}


@app.get("/")
def index():
    return {
        "service": "SDOC Hackathon Inbox",
        "endpoints": {
            "GET /emails": "list all email records",
            "GET /emails/{email_id}": "one email record",
            "GET /attachments/{path}": "download an SI/BL attachment",
            "GET /sample_submission": "the output shape you must produce",
            "POST /submit": "score your submission (JSON body: {email_id: {...}})",
        },
        "note": "Ground truth is private. Score yourself via POST /submit.",
    }


@app.get("/emails")
def list_emails():
    return _load_inbox()


@app.get("/emails/{email_id}")
def get_email(email_id: str):
    p = INBOX_DIR / f"{email_id}.json"
    if not p.exists():
        raise HTTPException(404, f"no such email: {email_id}")
    return json.loads(p.read_text())


@app.get("/attachments/{path:path}")
def get_attachment(path: str):
    # normalise and confine to ATTACH_DIR (no path traversal)
    target = (ATTACH_DIR / path).resolve()
    if not str(target).startswith(str(ATTACH_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, f"no such attachment: {path}")
    return FileResponse(target)


@app.get("/sample_submission")
def sample_submission():
    if not SAMPLE_PATH.exists():
        raise HTTPException(404, "sample_submission.json not found")
    return json.loads(SAMPLE_PATH.read_text())


@app.post("/submit")
async def submit(request: Request):
    """Score a submission against the private ground truth. The ground truth is
    never returned — only the scoreboard."""
    try:
        sub = await request.json()
    except Exception:
        raise HTTPException(400, "body must be JSON: {email_id: {category,status,has_defect,defect_fields}}")
    if not isinstance(sub, dict):
        raise HTTPException(400, "submission must be a JSON object keyed by email_id")
    truth = _load_ground_truth()
    result = scoring.score_all(truth, sub)
    return JSONResponse(result)


# --------------------------------------------------------------------------
# judge-only (disabled by default)
# --------------------------------------------------------------------------
@app.get("/ground_truth")
def ground_truth(x_judge_token: Optional[str] = Header(default=None)):
    if not REVEAL_GT:
        raise HTTPException(404, "not found")
    if JUDGE_TOKEN and x_judge_token != JUDGE_TOKEN:
        raise HTTPException(403, "bad judge token")
    return _load_ground_truth()
