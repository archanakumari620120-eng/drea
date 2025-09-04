import os
import json
import random
import requests
from pathlib import Path
import subprocess
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import schedule
import time

# ---------------- Load config ----------------
with open("config.json", "r") as f:
    CONFIG = json.load(f)

CLIENT_ID = CONFIG["client_id"]
CLIENT_SECRET = CONFIG["client_secret"]
REFRESH_TOKEN = CONFIG["refresh_token"]
API_KEY = CONFIG["api_key"]
GEMINI_API_KEY = CONFIG["gemini_api_key"]
HF_TOKEN = CONFIG["hf_token"]
PEXELS_KEY = CONFIG.get("pexels_api_key", None)

UPLOAD_INTERVAL_HOURS = CONFIG.get("upload_interval_hours", 5)
VIDEO_LENGTH = CONFIG.get("video_length_sec", 15)
RESOLUTION = CONFIG.get("target_resolution", [1080, 1920])
TITLE_TEMPLATE = CONFIG.get("video_title_template", "AI Shorts - {prompt}")
DESCRIPTION_TEMPLATE = CONFIG.get("video_description_template", "Generated with AI\nPrompt: {prompt}")
TAGS = CONFIG.get("video_tags", ["AI", "shorts", "trending"])
VISIBILITY = CONFIG.get("visibility", "public")

# ---------------- Manual image picker ----------------
def pick_manual_image(images_dir="images"):
    IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
    p = Path(images_dir)
    if not p.exists():
        return None
    files = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        if any(part.startswith(".") for part in f.parts):
            continue
        if f.suffix.lower() in IMG_EXT:
            files.append(str(f))
    if not files:
        return None
    choice = random.choice(files)
    print("[LOG] pick_manual_image ->", choice)
    return choice

# ---------------- Local music picker ----------------
def pick_local_music(music_dir="music"):
    AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac", ".opus", ".wma", ".mkv", ".mp4"}
    p = Path(music_dir)
    if not p.exists():
        return None
    files = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        if any(part.startswith(".") for part in f.parts):
            continue
        if f.suffix.lower() in AUDIO_EXT:
            files.append(str(f))
    if not files:
        return None
    choice = random.choice(files)
    print("[LOG] pick_local_music ->", choice)
    return choice

# ---------------- AI Prompt Generator ----------------
def generate_prompt():
    try:
        # Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": "Generate a short creative prompt for a video."}]}]}
        r = requests.post(url, json=payload, timeout=15)
        if r.ok:
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            print("[LOG] Gemini prompt ->", txt)
            return txt
    except Exception as e:
        print("[WARN] Gemini failed:", e)

    try:
        # HuggingFace fallback
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        r = requests.post("https://api-inference.huggingface.co/models/gpt2",
                          headers=headers, json={"inputs": "Generate a short creative prompt for a video."}, timeout=15)
        if r.ok:
            txt = r.json()[0]["generated_text"]
            print("[LOG] HF prompt ->", txt)
            return txt
    except Exception as e:
        print("[WARN] HuggingFace failed:", e)

    return "Beautiful AI generated video"

# ---------------- Image Source ----------------
def get_image(prompt):
    if PEXELS_KEY:
        try:
            headers = {"Authorization": PEXELS_KEY}
            r = requests.get(f"https://api.pexels.com/v1/search?query={prompt}&per_page=10", headers=headers, timeout=15)
            if r.ok and r.json()["photos"]:
                url = random.choice(r.json()["photos"])["src"]["original"]
                out = "temp_image.jpg"
                with open(out, "wb") as f:
                    f.write(requests.get(url).content)
                print("[LOG] Pexels image downloaded")
                return out
        except Exception as e:
            print("[WARN] Pexels failed:", e)

    return pick_manual_image()

# ---------------- Music Source ----------------
def get_music():
    local = pick_local_music()
    if local:
        return local
    try:
        cmd = ["yt-dlp", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3",
               "-o", "temp_music.%(ext)s", CONFIG["music_search_query"]]
        subprocess.run(cmd, check=True)
        print("[LOG] Downloaded music from YouTube")
        return "temp_music.mp3"
    except Exception as e:
        print("[WARN] Music fetch failed:", e)
        return None

# ---------------- Dummy video generator ----------------
def generate_video(image_path, music_path, output="output.mp4"):
    # Simple ffmpeg (no moviepy needed)
    try:
        cmd = [
            "ffmpeg", "-loop", "1", "-i", image_path,
            "-i", music_path,
            "-c:v", "libx264", "-t", str(VIDEO_LENGTH),
            "-pix_fmt", "yuv420p", "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}",
            "-y", output
        ]
        subprocess.run(cmd, check=True)
        print("[LOG] Video generated:", output)
        return output
    except Exception as e:
        print("[ERROR] ffmpeg failed:", e)
        return None

# ---------------- YouTube Upload ----------------
def upload_to_youtube(file_path, prompt):
    creds = Credentials.from_authorized_user_info({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    })

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": TITLE_TEMPLATE.format(prompt=prompt[:70]),
            "description": DESCRIPTION_TEMPLATE.format(prompt=prompt),
            "tags": TAGS,
            "categoryId": "22"
        },
        "status": {"privacyStatus": VISIBILITY}
    }

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=file_path
        )
        response = request.execute()
        print("[LOG] Uploaded video:", response["id"])
        return response
    except Exception as e:
        print("[ERROR] Upload failed:", e)
        return None

# ---------------- Main Job ----------------
def job():
    prompt = generate_prompt()
    img = get_image(prompt)
    music = get_music()
    if not img or not music:
        print("[ERROR] Missing image or music")
        return
    video = generate_video(img, music)
    if video:
        upload_to_youtube(video, prompt)

# ---------------- Scheduler ----------------
print(f"[LOG] Scheduler started. Interval = {UPLOAD_INTERVAL_HOURS} hours")
schedule.every(UPLOAD_INTERVAL_HOURS).hours.do(job)

job()  # run immediately first time

while True:
    schedule.run_pending()
    time.sleep(60)
        
