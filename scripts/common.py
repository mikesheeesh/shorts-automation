import json
import shutil
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")
SCRIPTS_POOL_PATH = os.path.join(ROOT, "content", "scripts_pool.json")
ASSETS_DIR = os.path.join(ROOT, "assets")
CACHE_DIR = os.path.join(ASSETS_DIR, "cache")
OUTPUT_DIR = os.path.join(ROOT, "output")
CREDENTIALS_DIR = os.path.join(ROOT, "credentials")
LOGS_DIR = os.path.join(ROOT, "logs")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    if os.environ.get("PEXELS_API_KEY"):
        config["pexels_api_key"] = os.environ["PEXELS_API_KEY"]
    return config


def load_scripts_pool():
    with open(SCRIPTS_POOL_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_scripts_pool(scripts):
    with open(SCRIPTS_POOL_PATH, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)


def find_ffmpeg_tool(name):
    path = shutil.which(name)
    if path:
        return path
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        matches = glob.glob(
            os.path.join(local_appdata, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "**", f"{name}.exe"),
            recursive=True,
        )
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"'{name}' not found on PATH and not found in the winget install location. "
        "Install it (winget install Gyan.FFmpeg) or open a new terminal so PATH updates."
    )


def find_font():
    candidates = [
        os.path.join(ROOT, "assets", "fonts", "caption_font.ttf"),
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError("No usable font file found (checked bundled assets/fonts/ and system fonts)")


def ensure_dirs():
    for d in (ASSETS_DIR, CACHE_DIR, OUTPUT_DIR, CREDENTIALS_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)
