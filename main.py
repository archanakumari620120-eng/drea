import os
import random
import requests
import schedule
import time
import json
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# ==== CONFIG ====
OUTPUT_VIDEO = "output.mp4"
VIDEO_LENGTH = 30  # sec
RES = (1080, 1920)
UPLOAD_INTERVAL = 5 * 60 * 60  # 5 ghante

# ==== ENV KEYS ====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")
YT_API_KEY = os.getenv("YT_API_KEY")

# ==== HELPERS ====

def generate_prompt():
    """Try Gemini -> HuggingFace -> fallback"""
    prompt = None
    try:
        if GEMINI_API_KEY:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": GEMINI_API_KEY},
                json={"contents":[{"parts":[{"text":"Generate YouTube Shorts title, description and 5 tags about motivation."}]}]}
            )
            data = resp.json()
            prompt = data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass

    if not prompt and HF_TOKEN:
        try:
            resp = requests.post(
                "https://api-inference.huggingface.co/models/gpt2",
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs":"Generate YouTube Shorts title, description and 5 tags about motivation."}
            )
            data = resp.json()
            prompt = data[0]["generated_text"]
        except:
            pass

    if not prompt:
        prompt = "Motivation to never give up | Keep pushing forward!\nDescription: Short motivational clip.\nTags: motivation, success, hustle, goals, inspiration"

    return prompt

def fetch_image():
    """Try Pexels -> manual fallback"""
    if PEXELS_API_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search?query=motivation&per_page=1",
                             headers={"Authorization": PEXELS_API_KEY})
            data = r.json()
            if data["photos"]:
                img_url = data["photos"][0]["src"]["large2x"]
                img_data = requests.get(img_url).content
                with open("image.jpg", "wb") as f:
                    f.write(img_data)
                return "image.jpg"
        except:
            pass

    # fallback manual
    if os.path.exists("images"):
        imgs = [os.path.join("images", x) for x in os.listdir("images")]
        if imgs:
            return random.choice(imgs)

    return None

def fetch_music():
    if os.path.exists("music"):
        musics = [os.path.join("music", x) for x in os.listdir("music")]
        if musics:
            return random.choice(musics)
    return None

def create_video(img_path, music_path):
    img_clip = ImageClip(img_path).set_duration(VIDEO_LENGTH).resize(RES)
    if music_path:
        audio = AudioFileClip(music_path).subclip(0, VIDEO_LENGTH)
        img_clip = img_clip.set_audio(audio)
    img_clip.write_videofile(OUTPUT_VIDEO, fps=30)

def upload_to_youtube(title, description, tags):
    creds = Credentials.from_authorized_user_info({
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "refresh_token": YT_REFRESH_TOKEN
    })

    youtube = build("youtube", "v3", credentials=creds)

    body = {
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
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=OUTPUT_VIDEO
    )
    response = request.execute()
    print("✅ Uploaded:", response["id"])

def job():
    print("🚀 Starting new cycle...")
    text = generate_prompt()
    lines = text.split("\n")
    title = lines[0].replace("Title:", "").strip()
    description = lines[1].replace("Description:", "").strip() if len(lines) > 1 else "Motivational Shorts"
    tags = []
    if len(lines) > 2:
        tags = [t.strip() for t in lines[-1].replace("Tags:", "").split(",")]

    img = fetch_image()
    music = fetch_music()
    if img:
        create_video(img, music)
        upload_to_youtube(title, description, tags)
    else:
        print("❌ No image found!")

if _name_ == "_main_":
    main()
    job()
    schedule.every(UPLOAD_INTERVAL).seconds.do(job)
    while True:
        schedule.run_pending()
        time.sleep(10)
