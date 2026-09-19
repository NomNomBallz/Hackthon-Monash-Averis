# SDOC Hackathon — Docker distribution (ORGANIZERS)

Self-contained. Unzip into a folder Docker can share (your home or Documents —
**not** `/tmp`, which Docker Desktop on macOS does not bind-mount), then run:

```bash
docker compose up --build
# serves on http://localhost:8080
```

> If `GET /health` shows `"emails": 0`, the bind mount is empty — you unzipped
> into a path Docker can't share. Move the folder under your home directory and
> retry.

- `GET  /emails`, `/emails/{id}`, `/attachments/{path}` — the inbox (no labels)
- `GET  /sample_submission` — the required output shape
- `POST /submit` — score a submission → scoreboard JSON

Ground truth (`data_v2/ground_truth.json`) is mounted privately at `/secrets`
and used only for scoring — it is never returned by any endpoint.

Score a submission from the terminal instead of over HTTP:

```bash
docker compose run --rm inbox python score_cli.py /path/inside/container.json
# or, without Docker:
cd server && python3 score_cli.py submission.json
```

⚠️ This package includes the answer key. Do NOT hand it to participants — give
them the participant bundle (`sdoc-hackathon-bundle.zip`) instead.

Change the published port by editing `ports:` in `docker-compose.yml`
(default `8080:8000`).
