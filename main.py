import os
import random
import datetime
import requests
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ---------- CONFIG ----------
IMAGE_FOLDER = "images"
MUSIC_FOLDER = "music"
TEMP_VIDEO = "temp_video.mp4"
TOKEN_FILE = "token.json"
CONFIG_FILE = "config.json"

# Prompts pool (random topic har bar)
PROMPTS = [
    "Stay positive, work hard, and make it happen!",
    "Success is the sum of small efforts repeated every day.",
    "Never give up, great things take time.",
    "Push yourself, because no one else is going to do it for you.",
    "Dream big, start small, act now.",
    "Discipline is the bridge between goals and accomplishment.",
    "Your only limit is your mind.",
    "Do something today that your future self will thank you for.",
    "Don’t stop when you’re tired, stop when you’re done."
]

# ---------- FUNCTIONS ----------
def get_random_image():
    if not os.path.exists(IMAGE_FOLDER):
        raise Exception("❌ images folder missing!")
    images = [os.path.join(IMAGE_FOLDER, f) for f in os.listdir(IMAGE_FOLDER)]
    if not images:
        raise Exception("❌ No images found in images/")
    return random.choice(images)

def get_random_music():
    if not os.path.exists(MUSIC_FOLDER):
        raise Exception("❌ music folder missing!")
    music = [os.path.join(MUSIC_FOLDER, f) for f in os.listdir(MUSIC_FOLDER)]
    if not music:
        raise Exception("❌ No music found in music/")
    return random.choice(music)

def create_video(image_path, music_path, output_path):
    clip = ImageClip(image_path).set_duration(30).resize((1080, 1920))
    audio = AudioFileClip(music_path).subclip(0, 30)
    final = clip.set_audio(audio)
    final.write_videofile(output_path, fps=24)
    return output_path

def upload_to_youtube(video_path, title, description, tags):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, ["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print("✅ Uploaded:", response["id"])

# ---------- MAIN ----------
if __name__ == "__main__":
    try:
        prompt = random.choice(PROMPTS)
        image = get_random_image()
        music = get_random_music()

        video = create_video(image, music, TEMP_VIDEO)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        title = f"{prompt} | Shorts #{random.randint(1000,9999)}"
        description = f"{prompt}\n\nUploaded at {now}"
        tags = ["motivation", "shorts", "inspiration", "life", "success"]

        upload_to_youtube(video, title, description, tags)

        os.remove(video)
        print("🎉 Done! One video uploaded successfully.")

    except Exception as e:
        print("❌ Error:", str(e))
        
