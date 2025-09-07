import os
import random
import time
import json
import base64
import requests
import schedule
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ✅ Pillow v10+ fix
if hasattr(Image, "Resampling"):
    RESAMPLE = Image.Resampling.LANCZOS
else:
    RESAMPLE = Image.ANTIALIAS

# Load config
with open("config.json", "r") as f:
    CONFIG = json.load(f)

# Paths
IMAGES_DIR = "images"
MUSIC_DIR = "music"
OUTPUTS_DIR = "outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# YouTube Auth
creds = Credentials.from_authorized_user_file("token.json")

# ---------------- Gemini Prompt ----------------
def generate_prompt():
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={CONFIG['gemini_api_key']}"
        payload = {"contents": [{"parts": [{"text": "Generate a short motivational title for YouTube Shorts"}]}]}
        r = requests.post(url, json=payload, timeout=20)
        if r.ok:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print("⚠️ Gemini prompt failed:", e)

    # fallback
    return random.choice([
        "Stay strong, keep moving!",
        "Push harder every day!",
        "Small steps big results!",
        "Dream it, do it!"
    ])

# ---------------- Gemini Video (experimental placeholder) ----------------
def generate_gemini_video(prompt):
    try:
        # Future Gemini video generation (currently unsupported)
        print("⚠️ Gemini video generation not available, skipping...")
        return None
    except Exception as e:
        print("⚠️ Gemini video failed:", e)
    return None

# ---------------- Gemini Image ----------------
def generate_gemini_image(prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={CONFIG['gemini_api_key']}"
        payload = {"contents": [{"parts": [{"text": f"Generate a motivational poster for: {prompt}"}]}]}
        r = requests.post(url, json=payload, timeout=30)
        if r.ok:
            # Gemini mostly text only, no direct image
            print("⚠️ Gemini image not directly supported, skipping...")
            return None
    except Exception as e:
        print("⚠️ Gemini image failed:", e)
    return None

# ---------------- HuggingFace Image ----------------
def generate_hf_image(prompt):
    try:
        headers = {"Authorization": f"Bearer {CONFIG['hf_token']}"}
        url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
        r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
        if r.ok:
            img_path = os.path.join(OUTPUTS_DIR, "ai_generated.jpg")
            with open(img_path, "wb") as f:
                f.write(r.content)
            return img_path
    except Exception as e:
        print("⚠️ HuggingFace failed:", e)
    return None

# ---------------- Video Generator ----------------
def generate_video():
    try:
        # 1️⃣ Prompt
        prompt = generate_prompt()
        print("📝 Prompt:", prompt)

        # 2️⃣ Try Gemini video
        vid_path = generate_gemini_video(prompt)
        if vid_path:
            return vid_path, prompt

        # 3️⃣ Try Gemini image
        img_path = generate_gemini_image(prompt)

        # 4️⃣ If no Gemini image → Hugging Face
        if not img_path:
            img_path = generate_hf_image(prompt)

        # 5️⃣ Final fallback → local image
        if not img_path:
            images = [os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR)
                      if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            if not images:
                print("❌ No images found.")
                return None, prompt
            img_path = random.choice(images)

        # Resize
        img = Image.open(img_path)
        img = img.resize((1080, 1920), RESAMPLE)
        fixed_img_path = os.path.join(OUTPUTS_DIR, "fixed.jpg")
        img.save(fixed_img_path)

        # Pick music
        musics = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        if not musics:
            print("❌ No music found.")
            return None, prompt
        music_path = random.choice(musics)

        # Create video
        clip = ImageClip(fixed_img_path, duration=30)
        audio = AudioFileClip(music_path).subclip(0, 30)
        clip = clip.set_audio(audio)
        out_path = os.path.join(OUTPUTS_DIR, "short.mp4")
        clip.write_videofile(out_path, fps=24)

        return out_path, prompt

    except Exception as e:
        print(f"❌ Video generation error: {e}")
        return None, "Motivational Short"

# ---------------- YouTube Upload ----------------
def upload_video(file_path, prompt):
    try:
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": prompt,
                    "description": f"AI Motivational Short: {prompt}",
                    "tags": ["AI", "shorts", "motivation", "automation"]
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(file_path)
        )
        response = request.execute()
        print("✅ Uploaded:", response["id"])
    except Exception as e:
        print(f"❌ Upload error: {e}")

# ---------------- Job ----------------
def job():
    print("🚀 Starting cycle...")
    file_path, prompt = generate_video()
    if file_path:
        upload_video(file_path, prompt)

if __name__ == "__main__":
    job()
     
