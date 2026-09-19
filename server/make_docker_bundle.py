#!/usr/bin/env python3
"""
make_docker_bundle.py — package the runnable Docker distribution (ORGANIZERS).

Produces a self-contained folder + zip that an organizer can unzip anywhere and
run with a single `docker compose up --build`. It includes the full dataset
AND ground_truth.json (the server needs it to score; it is served privately,
never exposed on an endpoint).

    python make_docker_bundle.py                 # -> ../sdoc-hackathon-docker/ + .zip
    python make_docker_bundle.py --no-zip

Layout of the produced bundle (top level, so compose's ./server and ./data_v2
relative paths resolve):

    sdoc-hackathon-docker/
    ├── docker-compose.yml
    ├── README.md                 how to run it
    ├── server/                   app.py, scoring.py, Dockerfile, ...
    └── data_v2/                  inbox/, attachments/, ground_truth.json, ...

⚠️ This bundle contains ground_truth.json — it is for ORGANIZERS/JUDGES, not
participants. Give participants sdoc-hackathon-bundle.zip instead.
"""
import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

RUN_README = """# SDOC Hackathon — Docker distribution (ORGANIZERS)

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
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "sdoc-hackathon-docker"))
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    def ignore(_dir, names):
        # skip caches / OS cruft so the zip is clean
        return [n for n in names if n in {"__pycache__", ".DS_Store"}]

    shutil.copytree(ROOT / "server", out / "server", ignore=ignore)
    shutil.copytree(ROOT / "data_v2", out / "data_v2", ignore=ignore)
    shutil.copy2(ROOT / "docker-compose.yml", out / "docker-compose.yml")
    (out / "README.md").write_text(RUN_README)

    # sanity: the pieces compose needs must be present
    assert (out / "docker-compose.yml").exists()
    assert (out / "server" / "Dockerfile").exists()
    assert (out / "data_v2" / "ground_truth.json").exists(), "organizer bundle must include the key"
    n_in = len(list((out / "data_v2" / "inbox").glob("email_*.json")))
    print(f"Docker bundle -> {out}")
    print(f"  emails: {n_in}, includes ground_truth.json: True (organizer/judge only)")

    if not args.no_zip:
        archive = shutil.make_archive(str(out), "zip", root_dir=out)
        print(f"  zip: {archive}")


if __name__ == "__main__":
    main()
