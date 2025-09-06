import os
import random
import time
import json
import schedule
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ✅ Safe resampling (fix for Pillow v10+)
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

def generate_video():
    try:
        # Pick random image
        images = [os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            print("❌ No images found in 'images/' folder.")
            return None
        img_path = random.choice(images)

        # Resize
        img = Image.open(img_path)
        img = img.resize((1080, 1920), RESAMPLE)
        fixed_img_path = os.path.join(OUTPUTS_DIR, "fixed.jpg")
        img.save(fixed_img_path)

        # Pick random music
        musics = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        if not musics:
            print("❌ No music found in 'music/' folder.")
            return None
        music_path = random.choice(musics)

        # Create video
        clip = ImageClip(fixed_img_path, duration=30)
        audio = AudioFileClip(music_path).subclip(0, 30)
        clip = clip.set_audio(audio)
        out_path = os.path.join(OUTPUTS_DIR, "short.mp4")
        clip.write_videofile(out_path, fps=24)

        return out_path

    except Exception as e:
        print(f"❌ Error in video generation: {e}")
        return None

def upload_video(file_path):
    try:
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": "AI Generated Short",
                    "description": "Automated YouTube Short",
                    "tags": ["AI", "shorts", "automation"]
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(file_path)
        )
        response = request.execute()
        print("✅ Video uploaded:", response["id"])
    except Exception as e:
        print(f"❌ Error in upload: {e}")

def job():
    print("🚀 Starting cycle...")
    file_path = generate_video()
    if file_path:
        upload_video(file_path)
if __name__ == "__main__":
    job()  # ek video generate + upload
    
