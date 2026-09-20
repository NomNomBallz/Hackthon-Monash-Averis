import os
import json
import time
from src.extractor import extract_si_bl_pair


def test_email_by_id(email_id: str, inbox_dir: str = "data_v2/inbox") -> dict:
    json_path = os.path.join(inbox_dir, f"{email_id}.json")
    if not os.path.exists(json_path):
        print(f"Error: Email file non-existent at {json_path}")
        return {}

    with open(json_path, "r", encoding="utf-8") as f:
        email_record = json.load(f)

    attachments = email_record.get("attachments", [])
    if len(attachments) < 2:
        return {
            "status": "SKIPPED",
            "source": None,
            "si_data": None,
            "bl_data": None,
            "error": "Less than 2 attachments present in email record."
        }

    si_path = attachments[0] if os.path.exists(attachments[0]) else os.path.join("data_v2", attachments[0])
    bl_path = attachments[1] if os.path.exists(attachments[1]) else os.path.join("data_v2", attachments[1])

    return extract_si_bl_pair(si_path, bl_path)


def run_full_inbox_test(
    inbox_dir: str = "data_v2/inbox", 
    output_json_path: str = "extracted_data_sample.json"
) -> dict:
    if not os.path.exists(inbox_dir):
        print(f"Error: Inbox directory not found at {inbox_dir}")
        return {}

    # Read and sort all email JSON files in the inbox
    all_files = sorted([f for f in os.listdir(inbox_dir) if f.endswith(".json")])
    total_emails = len(all_files)

    results = {}
    processed_count = 0
    success_count = 0
    unreadable_count = 0
    skipped_count = 0

    print(f"\n==========================================")
    print(f" Running Extraction Check Across ALL {total_emails} Emails")
    print(f"==========================================\n")

    batch_start_time = time.time()

    for idx, file_name in enumerate(all_files, 1):
        email_id = file_name.replace(".json", "")
        file_path = os.path.join(inbox_dir, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            record = json.load(f)

        attachments = record.get("attachments", [])

        if len(attachments) >= 2:
            processed_count += 1
            print(f"[{idx}/{total_emails}] Processing {email_id} ... ", end="", flush=True)

            pair_start = time.time()
            output = test_email_by_id(email_id, inbox_dir=inbox_dir)
            pair_elapsed = time.time() - pair_start

            status = output.get("status", "UNKNOWN")
            source = output.get("source", "N/A")

            if status == "SUCCESS":
                success_count += 1
                print(f"SUCCESS via {source} ({pair_elapsed:.2f}s)")
            else:
                unreadable_count += 1
                print(f"UNREADABLE ({output.get('error')})")

            results[email_id] = output
        else:
            skipped_count += 1

    total_time = time.time() - batch_start_time
    avg_time = total_time / processed_count if processed_count > 0 else 0.0

    # Save complete extracted dataset to JSON for your teammate
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n==========================================")
    print(" FULL INBOX EXTRACTION SUMMARY")
    print("==========================================")
    print(f" Total Emails Evaluated : {total_emails}")
    print(f" Document Pairs Tested  : {processed_count}")
    print(f" Successful Extractions : {success_count}")
    print(f" Unreadable / Escalated : {unreadable_count}")
    print(f" Skipped (<2 files)    : {skipped_count}")
    print(f" Total Runtime          : {total_time:.2f}s ({total_time/60:.2f}m)")
    print(f" Avg Time per Pair      : {avg_time:.2f}s")
    print(f" Saved Output File      : {output_json_path}")
    print("==========================================\n")

    return results


if __name__ == "__main__":
    run_full_inbox_test()