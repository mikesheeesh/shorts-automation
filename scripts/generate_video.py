"""Renders one script entry from scripts_pool.json into a finished vertical mp4.

Pipeline per segment: TTS audio (edge-tts) -> matching background clip (Pexels) ->
crop/loop to audio duration -> burn in on-screen text -> concat all segments'
video+audio -> final mux.
"""
import argparse
import asyncio
import hashlib
import os
import subprocess
import sys
import tempfile

import requests
import edge_tts

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    load_config, load_scripts_pool, find_ffmpeg_tool, find_font,
    ensure_dirs, CACHE_DIR, OUTPUT_DIR,
)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


def ffprobe_duration(ffprobe, path):
    out = subprocess.check_output([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ])
    return float(out.decode().strip())


def synth_segment_audio(text, voice, out_path):
    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)
    asyncio.run(_run())


def pexels_find_video_url(query, api_key):
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": "portrait", "per_page": 6}
    resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        params["orientation"] = "landscape"
        resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels videos found for query: {query!r}")

    best_url = None
    best_score = -1
    for video in videos:
        for vf in video.get("video_files", []):
            if vf.get("file_type") != "video/mp4":
                continue
            w, h = vf.get("width") or 0, vf.get("height") or 0
            portrait_bonus = 1000 if h > w else 0
            size_score = min(w * h, 1920 * 1080)
            score = portrait_bonus + size_score
            if score > best_score:
                best_score = score
                best_url = vf["link"]
    if not best_url:
        raise RuntimeError(f"No usable mp4 file for query: {query!r}")
    return best_url


def get_background_clip(query, api_key):
    ensure_dirs()
    key = hashlib.md5(query.encode("utf-8")).hexdigest()
    cached_path = os.path.join(CACHE_DIR, f"{key}.mp4")
    if os.path.exists(cached_path):
        return cached_path
    url = pexels_find_video_url(query, api_key)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(cached_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    return cached_path


def escape_drawtext(text):
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "’")
        .replace("%", "\\%")
    )


def escape_font_path(font_path):
    return font_path.replace("\\", "/").replace(":", "\\:")


def build_segment_clip(ffmpeg, raw_video, duration, on_screen_text, font_path, width, height, fps, out_path):
    escaped = escape_drawtext(on_screen_text)
    escaped_font = escape_font_path(font_path)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},"
        f"drawtext=fontfile='{escaped_font}':text='{escaped}':fontcolor=white:fontsize=64:"
        f"borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.72:line_spacing=10"
    )
    cmd = [
        ffmpeg, "-y",
        "-stream_loop", "-1", "-i", raw_video,
        "-t", str(duration),
        "-an", "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_files(ffmpeg, files, out_path, reencode_audio=False):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for path in files:
            abs_path = os.path.abspath(path).replace("\\", "/")
            escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
        list_path = f.name
    try:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path]
        if reencode_audio:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-c", "copy"]
        cmd.append(out_path)
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        os.unlink(list_path)


def mux_video_audio(ffmpeg, video_path, audio_path, out_path):
    cmd = [
        ffmpeg, "-y", "-i", video_path, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_video(script_entry, config, work_dir=None):
    ensure_dirs()
    ffmpeg = find_ffmpeg_tool("ffmpeg")
    ffprobe = find_ffmpeg_tool("ffprobe")
    font_path = find_font()
    voice = config.get("tts_voice", "en-US-GuyNeural")
    api_key = config["pexels_api_key"]
    width = config.get("video_width", 1080)
    height = config.get("video_height", 1920)
    fps = config.get("fps", 30)

    work_dir = work_dir or tempfile.mkdtemp(prefix=f"render_{script_entry['id']}_")
    os.makedirs(work_dir, exist_ok=True)

    audio_parts = []
    clip_parts = []

    for i, seg in enumerate(script_entry["segments"]):
        audio_path = os.path.join(work_dir, f"audio_{i}.mp3")
        synth_segment_audio(seg["voiceover"], voice, audio_path)
        duration = ffprobe_duration(ffprobe, audio_path)

        raw_bg = get_background_clip(seg["visual_prompt"], api_key)
        clip_path = os.path.join(work_dir, f"clip_{i}.mp4")
        build_segment_clip(ffmpeg, raw_bg, duration, seg["on_screen_text"], font_path, width, height, fps, clip_path)

        audio_parts.append(audio_path)
        clip_parts.append(clip_path)

    video_concat = os.path.join(work_dir, "video_concat.mp4")
    audio_concat = os.path.join(work_dir, "audio_concat.m4a")
    concat_files(ffmpeg, clip_parts, video_concat, reencode_audio=False)
    concat_files(ffmpeg, audio_parts, audio_concat, reencode_audio=True)

    out_path = os.path.join(OUTPUT_DIR, f"{script_entry['id']}.mp4")
    mux_video_audio(ffmpeg, video_concat, audio_concat, out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="script id from scripts_pool.json; defaults to first unused")
    args = parser.parse_args()

    config = load_config()
    if config.get("pexels_api_key", "").startswith("PUT_YOUR"):
        print("ERROR: set pexels_api_key in config.json first (see README.md).")
        sys.exit(1)

    scripts = load_scripts_pool()
    entry = None
    if args.id:
        entry = next((s for s in scripts if s["id"] == args.id), None)
        if not entry:
            print(f"No script with id {args.id!r} found.")
            sys.exit(1)
    else:
        entry = next((s for s in scripts if not s.get("used")), None)
        if not entry:
            print("No unused scripts left in the pool.")
            sys.exit(1)

    print(f"Rendering {entry['id']}...")
    out_path = generate_video(entry, config)
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()
