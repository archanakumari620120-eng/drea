import os
import random
import json
import time
import schedule
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from moviepy.editor import ImageSequenceClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime

# ---------------- CONFIG ----------------
with open("config.json") as f:
    CONFIG = json.load(f)

GEMINI_API_KEY = CONFIG.get("gemini_api_key", "")
HF_TOKEN = CONFIG.get("huggingface_token", "")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ---------------- AUTH ----------------
def authenticate_youtube():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=8081, prompt="consent", authorization_prompt_message="")
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

# ---------------- PROMPTS ----------------
def generate_prompt():
    prompts = [
        "A lone astronaut walking on Mars surface",
        "Cyberpunk neon futuristic city at night",
        "Medieval castle under the stars",
        "Ocean waves hitting golden sunset beach",
        "Abstract colorful AI dreamscape with lights"
    ]
    return random.choice(prompts)

# ---------------- IMAGE GENERATION ----------------
def generate_image_gemini(prompt):
    try:
        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent",
            headers=headers, json={"contents":[{"parts":[{"text": prompt}]}]}
        )
        if response.status_code == 200:
            return None  # Gemini image API placeholder
        return None
    except Exception as e:
        print("Gemini error:", e)
        return None

def generate_image_hf(prompt):
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(
            "https://api-inference.huggingface.co/models/prompthero/openjourney",
            headers=headers, json={"inputs": prompt}
        )
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        return None
    except Exception as e:
        print("HF error:", e)
        return None

def get_images(prompt):
    img = generate_image_gemini(prompt)
    if img: return [img]
    img = generate_image_hf(prompt)
    if img: return [img]

    fallback = [os.path.join("images", f) for f in os.listdir("images") if f.endswith((".jpg", ".png", ".jpeg"))]
    if fallback:
        return [Image.open(random.choice(fallback))]
    return []

# ---------------- VIDEO ----------------
def resize_images(images, size=(1080, 1920)):
    resized = []
    for img in images:
        if not isinstance(img, Image.Image):
            img = Image.open(img)
        resized.append(np.array(img.resize(size)))
    return resized

def pick_music():
    if not os.path.exists("music"):
        return None
    files = [os.path.join("music", f) for f in os.listdir("music") if f.endswith(".mp3")]
    return random.choice(files) if files else None

def create_video(images, audio_file, out_file="temp_video.mp4"):
    frames = resize_images(images)
    clip = ImageSequenceClip(frames, fps=24)

    if audio_file:
        try:
            audio = AudioFileClip(audio_file)
            clip = clip.set_audio(audio)
        except Exception as e:
            print("Skipping audio:", e)

    clip.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24)
    return out_file

# ---------------- YOUTUBE UPLOAD ----------------
def upload_to_youtube(youtube, video_file, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("✅ Uploaded:", f"https://youtu.be/{response['id']}")
    return response

# ---------------- MAIN JOB ----------------
def job():
    print(f"\n🕒 Running job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    youtube = authenticate_youtube()

    prompt = generate_prompt()
    print("🎨 Prompt:", prompt)

    images = get_images(prompt)
    if not images:
        print("❌ No images, skipping.")
        return

    music = pick_music()
    video_file = create_video(images, music)

    title = f"AI Shorts: {prompt}"
    description = f"Generated with AI\nPrompt: {prompt}"
    tags = ["AI", "Shorts", "Trending"]

    upload_to_youtube(youtube, video_file, title, description, tags)

    try:
        os.remove(video_file)
    except:
        pass

# ---------------- SCHEDULER ----------------
if __name__ == "__main__":
    schedule.every().day.at("04:00").do(job)
    schedule.every().day.at("08:00").do(job)
    schedule.every().day.at("11:58").do(job)
    schedule.every().day.at("17:00").do(job)
    schedule.every().day.at("22:00").do(job)

    print("📅 Scheduler started... Waiting for jobs...")
    while True:
        schedule.run_pending()
        time.sleep(30)
