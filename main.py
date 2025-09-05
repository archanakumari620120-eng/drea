import os
import random
import requests
import schedule
import time
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from PIL import Image
from datetime import datetime

# ================== CONFIG ==================
CONFIG = {
    "gemini_api_key": "AIzaSyCfSRrZHcSf1_NgrosBfP7hSd1j2c9uTuA",
    "hf_token": "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",
    "pexels_api_key": "YOUR_PEXELS_API_KEY",
    "video_length_sec": 15,
    "target_resolution": (1080, 1920),
    "upload_interval_hours": 5,
    "video_tags": ["AI", "shorts", "trending", "motivation", "inspiration"]
}

PROMPTS = [
    "Stay positive, work hard, make it happen!",
    "Believe in yourself and all that you are.",
    "Your only limit is your mind.",
    "Great things never come from comfort zones.",
    "Push yourself, because no one else is going to do it for you.",
    "Dream it. Wish it. Do it.",
    "Don’t stop until you’re proud.",
    "Stay hungry, stay foolish.",
    "Turn your wounds into wisdom.",
    "Work in silence, let success make the noise."
]

# ============= GEMINI / HF / PEXELS / MANUAL =============

def generate_prompt():
    return random.choice(PROMPTS)

def get_image_from_gemini(prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={CONFIG['gemini_api_key']}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if res.status_code == 200:
            return None  # Gemini free text-only → fallback
    except:
        pass
    return None

def get_image_from_hf(prompt):
    try:
        url = "https://api-inference.huggingface.co/models/prompthero/openjourney"
        headers = {"Authorization": f"Bearer {CONFIG['hf_token']}"}
        res = requests.post(url, headers=headers, json={"inputs": prompt})
        if res.status_code == 200:
            out_path = "temp_image.jpg"
            with open(out_path, "wb") as f:
                f.write(res.content)
            return out_path
    except:
        pass
    return None

def get_image_from_pexels(prompt):
    try:
        headers = {"Authorization": CONFIG["pexels_api_key"]}
        res = requests.get(f"https://api.pexels.com/v1/search?query={prompt}&per_page=1", headers=headers)
        data = res.json()
        if data["photos"]:
            img_url = data["photos"][0]["src"]["portrait"]
            img_data = requests.get(img_url).content
            out_path = "temp_image.jpg"
            with open(out_path, "wb") as f:
                f.write(img_data)
            return out_path
    except:
        pass
    return None

def get_manual_image():
    files = [f for f in os.listdir("images") if f.lower().endswith((".jpg", ".png"))]
    if files:
        return os.path.join("images", random.choice(files))
    return None

def get_music_file():
    files = [f for f in os.listdir("music") if f.lower().endswith(".mp3")]
    if files:
        return os.path.join("music", random.choice(files))
    return None

# ============= VIDEO CREATION =============

def create_video(image_path, music_path, output_path="output.mp4"):
    img = Image.open(image_path)
    img = img.resize(CONFIG["target_resolution"], Image.Resampling.LANCZOS)
    img.save("resized.jpg")

    clip = ImageClip("resized.jpg", duration=CONFIG["video_length_sec"])
    if music_path:
        audio = AudioFileClip(music_path).subclip(0, CONFIG["video_length_sec"])
        clip = clip.set_audio(audio)

    clip.write_videofile(output_path, fps=24)
    return output_path

# ============= YOUTUBE UPLOAD =============

def upload_to_youtube(video_file, title, description, tags):
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_file)
    )
    response = request.execute()
    print("✅ Video uploaded:", response["id"])

# ============= MAIN FLOW =============

def job():
    prompt = generate_prompt()
    print("🎯 Prompt:", prompt)

    image = get_image_from_gemini(prompt) or get_image_from_hf(prompt) or get_image_from_pexels(prompt) or get_manual_image()
    music = get_music_file()

    if not image or not music:
        print("⚠️ Missing image/music")
        return

    video_file = create_video(image, music)
    title = f"AI Shorts - {prompt}"
    description = f"Generated automatically with AI.\nPrompt: {prompt}"

    upload_to_youtube(video_file, title, description, CONFIG["video_tags"])

    os.remove(video_file)
    if os.path.exists("resized.jpg"):
        os.remove("resized.jpg")
    if image == "temp_image.jpg" and os.path.exists(image):
        os.remove(image)

# ============= SCHEDULER =============

schedule.every(CONFIG["upload_interval_hours"]).hours.do(job)

print("🚀 Bot started... (uploads every 5 hours)")
while True:
    schedule.run_pending()
    time.sleep(60)
