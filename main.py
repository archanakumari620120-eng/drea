import os
import random
import json
import time
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from PIL import Image, ImageDraw, ImageFont

# -------------------------------
# Load config
# -------------------------------
with open("config.json", "r") as f:
    CONFIG = json.load(f)

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# -------------------------------
# Pick random image & music
# -------------------------------
def pick_random_file(folder):
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    return os.path.join(folder, random.choice(files)) if files else None

# -------------------------------
# Generate video (1080x1920)
# -------------------------------
def generate_video():
    print("🎬 Generating video...")

    image_file = pick_random_file("images")
    music_file = pick_random_file("music")

    if not image_file or not music_file:
        raise FileNotFoundError("❌ Image or music file missing in images/ or music/ folder!")

    # Create image clip (background 1080x1920)
    img_clip = ImageClip(image_file).resize(height=1920).set_position("center").set_duration(30)

    # Add music
    audio_clip = AudioFileClip(music_file).subclip(0, 30)
    final_clip = img_clip.set_audio(audio_clip)

    output_path = "output.mp4"
    final_clip.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")
    return output_path

# -------------------------------
# Authenticate YouTube
# -------------------------------
def get_youtube_service():
    creds = Credentials.from_authorized_user_file("client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

# -------------------------------
# Upload to YouTube
# -------------------------------
def upload_video(file_path):
    youtube = get_youtube_service()

    request_body = {
        "snippet": {
            "title": f"Random Short #{random.randint(1000,9999)}",
            "description": "Auto-uploaded YouTube Short 🎬",
            "tags": ["shorts", "ai", "automation"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media_file = MediaFileUpload(file_path)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = request.execute()
    print(f"✅ Uploaded successfully! Video ID: {response['id']}")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    print("🚀 Job started...")
    try:
        video_file = generate_video()
        upload_video(video_file)
    except Exception as e:
        print(f"❌ ERROR: {e}")
