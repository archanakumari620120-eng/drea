[09:04, 4/9/2025] ᴬᵐᵃⁿ: import os
from moviepy.editor import ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Load config from environment
CFG = {
    "client_id": os.getenv("YT_CLIENT_ID"),
    "client_secret": os.getenv("YT_CLIENT_SECRET"),
    "refresh_token": os.getenv("YT_REFRESH_TOKEN"),
    "api_key": os.getenv("YT_API_KEY", ""),
    "visibility": "public"
}

# Step 1: Create dummy short video
def create_dummy_video(path="short.mp4"):
    clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=5)
    clip.write_videofile(path, fps=24)
    return path

# Step 2: Upload to YouTube
def upload_youtube(video_path, title="Test Video", desc="Uploaded via GitHub Actions")…
[09:13, 4/9/2025] ᴬᵐᵃⁿ: name: YouTube Shorts Auto Upload

on:
  workflow_dispatch:
  schedule:
    - cron: "0 */5 * * *"  # Har 5 ghante me run
  push:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Set up Python
        uses: actions/setup-python@f677139bbe7f9c59b41e40162b753c062f5d49a3
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run script
        env:
          YT_CLIENT_ID: ${{ secrets.YT_CLIENT_ID }}
          YT_CLIENT_SECRET: ${{ secrets.YT_CLIENT_SECRET }}
          YT_REFRESH_TOKEN: ${{ secrets.YT_REFRESH_TOKEN }}
        run: python main.py
[09:20, 4/9/2025] ᴬᵐᵃⁿ: import os
import json
from moviepy.editor import ImageClip, AudioFileClip
import schedule
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials


# ------------------- CONFIG LOAD -------------------
def load_config():
    config = {}
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except Exception as e:
        print("⚠️ Config.json load error:", e)

    # Env vars override config.json
    config["client_id"] = os.getenv("YT_CLIENT_ID", config.get("client_id"))
    config["client_secret"] = os.getenv("YT_CLIENT_SECRET", config.get("client_secret"))
    config["refresh_token"] = os.getenv("YT_REFRESH_TOKEN", config.get("refresh_token"))
    config["api_key"] = os.getenv("YT_API_KEY", config.get("api_key"))

    return config


CFG = load_config()


# ------------------- VIDEO GENERATOR -------------------
def generate_video():
    print("🎬 Generating video...")

    os.makedirs("outputs", exist_ok=True)

    # Example: ek static image se short banate hain
    clip = ImageClip("images/sample.jpg", duration=15).resize((1080, 1920))

    if os.path.exists("music/sample.mp3"):
        audio = AudioFileClip("music/sample.mp3").volumex(0.7)
        clip = clip.set_audio(audio)

    output_path = "outputs/short.mp4"
    clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    return output_path


# ------------------- YOUTUBE UPLOAD -------------------
def upload_youtube(video_file, title, desc, visibility="public"):
    print("📤 Uploading to YouTube...")

    creds = Credentials(
        None,
        refresh_token=CFG["refresh_token"],
        client_id=CFG["client_id"],
        client_secret=CFG["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
    )

    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": ["AI Shorts", "Automation"],
            "categoryId": "22",  # People & Blogs
        },
        "status": {"privacyStatus": visibility},
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    upload_request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = upload_request.next_chunk()
        if status:
            print(f"⬆️ Uploading... {int(status.progress() * 100)}%")

    print("✅ Upload complete:", response["id"])


# ------------------- MAIN -------------------
def main():
    print("🚀 Starting script...")

    video_path = generate_video()

    title = "AI Short - Demo"
    desc = "Generated automatically with AI"

    upload_youtube(video_path, title, desc, CFG.get("visibility", "public"))


if _name_ == "_main_":
    # Schedule: run every 5 hours (for example)
    schedule.every(5).hours.do(main)

    print("⏳ Scheduler started. Waiting for jobs...")
    while True:
        schedule.run_pending()
        time.sleep(10)
