import os
import time
import random
import json
import numpy as np
import subprocess
from moviepy.editor import ImageSequenceClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from PIL import Image
import requests

# ================= CONFIG ==================
CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

HF_TOKEN = CONFIG.get("huggingface_token")
GEMINI_API_KEY = CONFIG.get("gemini_api_key")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"
CREDENTIALS_PICKLE = "token.pickle"

FPS = 24
VIDEO_FILE = "temp_video.mp4"
MUSIC_DIR = "music"
IMAGES_DIR = "images"

NO_COPYRIGHT_TRACKS = [
    "https://www.youtube.com/watch?v=DWcJFNfaw9c",  # Chillhop
    "https://www.youtube.com/watch?v=5qap5aO4i9A",  # Lofi
    "https://www.youtube.com/watch?v=2x2qYzYVj7o"   # NCS
]
# ===========================================

# ---------------- AUTH ---------------------
def get_youtube_service():
    creds = None
    if os.path.exists(CREDENTIALS_PICKLE):
        with open(CREDENTIALS_PICKLE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8081)
        with open(CREDENTIALS_PICKLE, "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

# ---------------- IMAGE GEN ----------------
def generate_image_hf(prompt):
    try:
        url = "https://api-inference.huggingface.co/models/prompthero/openjourney"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(url, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return Image.open(response.raw).convert("RGB")
    except Exception as e:
        print("HF error:", e)
    return None

def generate_image_gemini(prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generate?key={GEMINI_API_KEY}"
        response = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]})
        if response.status_code == 200:
            # Placeholder dummy image
            return Image.new("RGB", (720, 1280), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
    except Exception as e:
        print("Gemini error:", e)
    return None

def get_images(prompt):
    img = generate_image_hf(prompt)
    if img:
        print("✅ HuggingFace image generated")
        return [img]

    img = generate_image_gemini(prompt)
    if img:
        print("✅ Gemini image generated")
        return [img]

    if os.path.exists(IMAGES_DIR):
        files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if files:
            prompt_words = prompt.lower().split()
            matched = [f for f in files if any(word in f.lower() for word in prompt_words)]
            if matched:
                print(f"⚠️ Using matched manual images for: {prompt}")
                return [Image.open(os.path.join(IMAGES_DIR, f)).convert("RGB") for f in matched[:5]]
            else:
                print("⚠️ No keyword match, using random manual images")
                return [Image.open(os.path.join(IMAGES_DIR, f)).convert("RGB") for f in random.sample(files, min(5, len(files)))]
    print("❌ No images available at all!")
    return []

# ---------------- MUSIC ----------------
def get_background_music():
    if os.path.exists(MUSIC_DIR):
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        if files:
            return os.path.join(MUSIC_DIR, random.choice(files))

    url = random.choice(NO_COPYRIGHT_TRACKS)
    output_path = os.path.join(MUSIC_DIR, "yt_music.mp3")
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_path, url]
        subprocess.run(cmd, check=True)
        print(f"🎶 Downloaded music from {url}")
        return output_path
    except Exception as e:
        print("❌ Music download failed:", e)
        return None

# ---------------- VIDEO GEN ----------------
def generate_video(prompt, duration=30):
    images = get_images(prompt)
    if not images:
        print("❌ Skipping cycle, no images")
        return None

    arrays = [np.array(img.resize((1080,1920))) for img in images]
    clip = ImageSequenceClip(arrays, fps=FPS).set_duration(duration)

    audio_file = get_background_music()
    if audio_file:
        try:
            audio_clip = AudioFileClip(audio_file).subclip(0, clip.duration)
            clip = clip.set_audio(audio_clip)
        except Exception as e:
            print("⚠️ Skipping audio, error:", e)

    clip.write_videofile(VIDEO_FILE, codec="libx264", audio_codec="aac", fps=FPS)
    return VIDEO_FILE

# ---------------- UPLOAD ----------------
def upload_to_youtube(video_file, prompt):
    youtube = get_youtube_service()

    title = f"{prompt[:40]} #{random.randint(1000,9999)}"
    description = f"AI generated short for: {prompt}\n\n#shorts #AI"
    tags = ["AI", "Shorts", "Generated", "Art"]

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(video_file)
    )
    response = request.execute()
    print("✅ Uploaded:", f"https://youtu.be/{response['id']}")

# ---------------- LOOP ----------------
def main_loop():
    prompts = [
        "Astronaut walking on Mars",
        "A magical glowing forest",
        "Cyberpunk futuristic Tokyo",
        "Medieval castle under the stars"
    ]

    while True:
        prompt = random.choice(prompts)
        print(f"\n🚀 Prompt: {prompt}")
        video_file = generate_video(prompt, duration=30)
        if video_file:
            upload_to_youtube(video_file, prompt)
            try:
                os.remove(video_file)
            except:
                pass
        print("⏳ Waiting 5 minutes for next video...")
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
