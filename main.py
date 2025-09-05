import os, random, time, schedule
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Config load
import json
with open("config.json") as f:
    config = json.load(f)

# Paths
IMAGE_DIR = "images"
MUSIC_DIR = "music"

def generate_video():
    print("🎬 Generating video...")
    # pick random image
    image_file = random.choice(os.listdir(IMAGE_DIR))
    img_path = os.path.join(IMAGE_DIR, image_file)
    clip = ImageClip(img_path, duration=10).resize((1080,1920))

    # pick random music
    music_file = random.choice(os.listdir(MUSIC_DIR))
    music_path = os.path.join(MUSIC_DIR, music_file)
    audio = AudioFileClip(music_path).subclip(0,10)

    clip = clip.set_audio(audio)
    clip.write_videofile("output.mp4", fps=24)
    return "output.mp4"

def upload_video(file_path):
    print("📤 Uploading video to YouTube...")
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"AI Generated Short {random.randint(1,1000)}",
                "description": "Auto-generated via script",
                "tags": ["AI","Shorts","Automation"]
            },
            "status": {"privacyStatus": "private"}
        },
        media_body=MediaFileUpload(file_path)
    )
    response = request.execute()
    print("✅ Uploaded:", response.get("id"))

def job():
    try:
        video_path = generate_video()
        upload_video(video_path)
    except Exception as e:
        print("❌ Error:", e)

# Run once for manual execution
if __name__ == "__main__":
    job()
