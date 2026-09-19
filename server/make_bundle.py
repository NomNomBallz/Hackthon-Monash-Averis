#!/usr/bin/env python3
"""
make_bundle.py — assemble the participant-facing bundle (ORGANIZERS).

Copies the dataset into a clean folder WITHOUT ground_truth.json, adds the
participant loader + a quick-start, and (optionally) zips it. Participants get
this; judges keep data_v2/ground_truth.json private.

    python make_bundle.py                     # -> ./sdoc-hackathon-bundle/
    python make_bundle.py --zip               # + sdoc-hackathon-bundle.zip
    python make_bundle.py --src ../data_v2 --out /tmp/bundle --zip

Contents of the bundle:
    inbox/                  520 email JSON files (no labels)
    attachments/            SI/BL docs (txt/pdf/docx/xlsx)
    sample_submission.json  the exact output shape to produce
    loader.py               one-import access (local files or HTTP server)
    README.md               participant quick-start
"""
import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).parent

QUICKSTART = """# SDOC Hackathon — participant bundle

Build a pipeline that reads this inbox and, for each email, decides:

1. **category** — one of `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`,
   `GENERAL`, `SPAM`.
2. for `BL_COMPARISON` emails, compare the **Shipping Instruction (SI)** against
   the **draft Bill of Lading (BL)** attachments and report the outcome:
   - `status`: `OK` (all 7 fields match), `MISMATCH` (≥1 field differs), or
     `NEEDS_REVIEW` (you cannot decide — unreadable/missing/wrong document).
   - `has_defect` + `defect_fields` when it's a `MISMATCH`.
   - `review_reason` when it's `NEEDS_REVIEW`
     (`wrong_doc_type` | `missing_attachment` | `unreadable` | `missing_value`).

The 7 compared fields: **shipper, consignee, notify_party, port_of_loading,
port_of_discharge, container_count, gross_weight_kg**. Note the SI and BL often
*label the same field differently* (`Port of Loading` vs `Load Port`) — align by
meaning, not by header text.

## Quick start

```bash
# look at one email + its documents
cat inbox/email_004.json
cat attachments/email_004_SI.txt
cat attachments/email_004_BL.txt

# or use the loader (stdlib only for the .txt path)
python3 -c "from loader import Inbox; ib=Inbox('.'); print(len(ib.emails()),'emails')"
```

```python
from loader import Inbox
inbox = Inbox(".")                     # this folder  (or a server URL)
submission = {}
for email in inbox:
    eid = email["email_id"]
    # ... your classify + extract + compare pipeline ...
    submission[eid] = {
        "category": "BL_COMPARISON",
        "status": "MISMATCH",
        "review_reason": None,
        "has_defect": True,
        "defect_fields": ["consignee"],
    }
import json; json.dump(submission, open("submission.json", "w"), indent=2)
```

Match **`sample_submission.json`** exactly (every email_id present).

## Scoring

You don't have the ground truth. Either:
- the organizers run `score_cli.py submission.json` for you, **or**
- if they gave you the HTTP server URL:
  ```python
  inbox = Inbox("http://<host>:8080")
  print(inbox.submit(submission)["final_score"])
  ```

Final score = 50% end-to-end (defects caught all the way through) + 30% Stage-1
macro-F1 + 20% Stage-3 defect-F1. `NEEDS_REVIEW` handling is reported as a
separate reliability axis.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE.parent / "data_v2"))
    ap.add_argument("--out", default=str(HERE.parent / "sdoc-hackathon-bundle"))
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "inbox").mkdir(parents=True)
    (out / "attachments").mkdir(parents=True)

    # copy inbox + attachments + sample submission  (NOT ground_truth.json)
    n_in = 0
    for p in sorted((src / "inbox").glob("email_*.json")):
        shutil.copy2(p, out / "inbox" / p.name)
        n_in += 1
    n_att = 0
    for p in sorted((src / "attachments").iterdir()):
        if p.is_file():
            shutil.copy2(p, out / "attachments" / p.name)
            n_att += 1
    shutil.copy2(src / "sample_submission.json", out / "sample_submission.json")
    shutil.copy2(HERE / "loader.py", out / "loader.py")
    (out / "README.md").write_text(QUICKSTART)

    # safety assertion: ground truth must never be in the bundle
    leaked = list(out.rglob("ground_truth*"))
    assert not leaked, f"ground truth leaked into bundle: {leaked}"

    print(f"Bundle -> {out}")
    print(f"  inbox: {n_in} emails, attachments: {n_att} files")
    print(f"  ground_truth.json present? {(out / 'ground_truth.json').exists()}  (must be False)")

    if args.zip:
        archive = shutil.make_archive(str(out), "zip", root_dir=out)
        print(f"  zip: {archive}")


if __name__ == "__main__":
    main()
