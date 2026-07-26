"""Orchestrator: picks the next unused script, renders it, uploads it to YouTube,
and logs the result. Meant to be triggered by Windows Task Scheduler 3-4x/day.

Usage:
  python main.py                  # render + upload next script, using config.json privacy setting
  python main.py --render-only    # just render an mp4, skip upload (for testing the pipeline)
  python main.py --privacy public # override privacy status for this run
"""
import argparse
import datetime
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, load_scripts_pool, save_scripts_pool, ensure_dirs, LOGS_DIR
from generate_video import generate_video
from upload_youtube import get_authenticated_service, upload_short

LOG_PATH = os.path.join(LOGS_DIR, "run_log.jsonl")


def log_event(event):
    ensure_dirs()
    event["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False))


def build_metadata(entry):
    title = entry["title_options"][0]
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    hashtags_line = " ".join(entry["hashtags"])
    description = f"{entry['caption']}\n\n{hashtags_line} #Shorts"
    tags = [h.lstrip("#") for h in entry["hashtags"]] + ["shorts", "psychology facts"]
    return title, description, tags


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true", help="skip the YouTube upload step")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default=None)
    parser.add_argument("--id", help="force a specific script id instead of the next unused one")
    args = parser.parse_args()

    config = load_config()
    if config.get("pexels_api_key", "").startswith("PUT_YOUR"):
        print("ERROR: set pexels_api_key in config.json first (see README.md).")
        sys.exit(1)

    scripts = load_scripts_pool()
    if args.id:
        entry = next((s for s in scripts if s["id"] == args.id), None)
        if not entry:
            print(f"No script with id {args.id!r} found.")
            sys.exit(1)
    else:
        entry = next((s for s in scripts if not s.get("used")), None)
        if not entry:
            log_event({"event": "pool_empty", "message": "No unused scripts left. Ask Claude to top up scripts_pool.json."})
            sys.exit(1)

    try:
        print(f"Rendering {entry['id']}...")
        video_path = generate_video(entry, config)
        log_event({"event": "rendered", "id": entry["id"], "path": video_path})
    except Exception as e:
        log_event({"event": "render_failed", "id": entry["id"], "error": str(e), "trace": traceback.format_exc()})
        sys.exit(1)

    if args.render_only:
        print(f"Render-only mode, skipping upload. File: {video_path}")
        return

    title, description, tags = build_metadata(entry)
    privacy = args.privacy or config.get("youtube_privacy_status", "private")

    try:
        youtube = get_authenticated_service()
        response = upload_short(
            youtube, video_path, title, description, tags,
            category_id=config.get("youtube_category_id", "22"),
            privacy_status=privacy,
        )
        video_id = response["id"]
        log_event({
            "event": "uploaded", "id": entry["id"], "youtube_id": video_id,
            "url": f"https://youtube.com/shorts/{video_id}", "privacy": privacy,
        })
    except Exception as e:
        log_event({"event": "upload_failed", "id": entry["id"], "error": str(e), "trace": traceback.format_exc()})
        sys.exit(1)

    entry["used"] = True
    save_scripts_pool(scripts)


if __name__ == "__main__":
    main()
