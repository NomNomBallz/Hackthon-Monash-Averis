# SDOC hackathon — delivery kit

Two ways to get the `data_v2/` dataset into participants' hands. The dataset is
the same either way; the difference is whether ground truth stays private and
whether scoring is centralised.

| | **A. Static bundle** | **B. Docker server** |
|---|---|---|
| Setup for participants | unzip, read files | hit an HTTP URL |
| Ground truth | withheld (you keep it) | private on the server, never served |
| Scoring | you run `score_cli.py` | participants `POST /submit`, or you do |
| Needs uptime during event | no | yes |
| Best when | open build / self-paced | scored competition |

You said ground truth is held until requested → **use both**: hand out the
static bundle so nobody is blocked, and (optionally) run the server for live
scoring.

---

## A. Static bundle (hand this to participants)

```bash
cd server
python3 make_bundle.py --zip
# -> ../sdoc-hackathon-bundle/  and  ../sdoc-hackathon-bundle.zip
```

The bundle contains `inbox/`, `attachments/`, `sample_submission.json`,
`loader.py`, and a participant `README.md`. It **never** contains
`ground_truth.json` (the builder asserts this).

To score a returned submission:

```bash
python3 score_cli.py path/to/submission.json          # uses ../data_v2/ground_truth.json
python3 score_cli.py submission.json --json            # machine-readable
```

## B. Docker server (`docker compose`)

```bash
docker compose up --build      # from the repo root; serves on http://localhost:8080
```

`data_v2/` is mounted read-only at `/data`; `ground_truth.json` is mounted
separately at `/secrets` and is only read server-side for scoring — it is not in
the served tree and has no public endpoint.

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + email count |
| GET | `/emails` | all email records (no labels) |
| GET | `/emails/{id}` | one email |
| GET | `/attachments/{path}` | download an SI/BL file |
| GET | `/sample_submission` | the required output shape |
| POST | `/submit` | score a submission → scoreboard JSON |
| GET | `/ground_truth` | **404 unless** `REVEAL_GT=1` (judge-only, token-gated) |

```bash
# participant scores themselves without ever seeing labels:
curl -s -X POST localhost:8080/submit \
  -H 'Content-Type: application/json' \
  --data-binary @submission.json | python3 -m json.tool
```

To let judges pull labels over HTTP, set in `docker-compose.yml`:
`REVEAL_GT: "1"` and `JUDGE_TOKEN: "<secret>"` (then send header
`X-Judge-Token: <secret>`).

Change the published port by editing the `ports:` mapping (default `8080:8000`).

---

## Files

```
server/
├── app.py             FastAPI service (serve + score)
├── scoring.py         v2-aware scoring (shared by server + CLI)
├── score_cli.py       judges: score a submission from the terminal
├── loader.py          participants: one-import access (local or HTTP)
├── make_bundle.py     organizers: build the participant bundle (strips GT)
├── requirements.txt   fastapi + uvicorn
└── Dockerfile
docker-compose.yml     at repo root
```

## Submission format

```json
{ "email_001": {
    "category": "BL_COMPARISON",
    "status": "MISMATCH",
    "review_reason": null,
    "has_defect": true,
    "defect_fields": ["consignee"]
} }
```

Every `email_id` must be present. See `data_v2/README.md` for the full schema,
categories, and how the dataset (incl. the 20 `NEEDS_REVIEW` edge cases) is
built.

## Scoring model

`final_score = 0.30·stage1_macroF1 + 0.20·stage3_defectF1 + 0.50·end_to_end`.
End-to-end (defects routed *and* flagged with the exact fields) is the headline.
The `NEEDS_REVIEW` edge cases are graded on a separate diagnostic reliability
axis (escalation precision/recall), so they don't distort the core leaderboard
unless you choose to weight them in.
