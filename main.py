import os
import random
import time
import json
import schedule
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ===== Load Config =====
with open("config.json", "r") as f:
    config = json.load(f)

# ===== YouTube Auth =====
def get_youtube_service():
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds)

# ===== Random Prompt Generator =====
prompts = [
    "Never give up on your dreams, success is closer than you think.",
    "Aaj ek nayi shuruaat karo – chhoti jeet badi jeet banegi.",
    "Discipline is the bridge between goals and accomplishment.",
    "Smile more, stress less, and make today count.",
    "Learn daily, grow daily – zindagi wahi hai jo aap banaate ho.",
    "Your vibe attracts your tribe – positive raho, positive milega.",
    "Hard work beats talent when talent doesn’t work hard.",
    "Khud pe vishwas rakho, duniya aapke peeche chalegi."
]

def get_random_prompt():
    return random.choice(prompts)

# ===== Video Generator =====
def generate_video():
    img_file = random.choice(os.listdir("images"))
    img_path = os.path.join("images", img_file)

    # --- Fix for PIL ANTIALIAS error ---
    img = Image.open(img_path)
    try:
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
    except AttributeError:
        img = img.resize((1080, 1920), Image.ANTIALIAS)
    img.save("temp.jpg")

    # Music select
    music_file = random.choice(os.listdir("music"))
    music_path = os.path.join("music", music_file)

    # Make clip
    img_clip = ImageClip("temp.jpg").set_duration(30)
    audio_clip = AudioFileClip(music_path).subclip(0, 30)
    final_clip = img_clip.set_audio(audio_clip)

    final_path = "final_video.mp4"
    final_clip.write_videofile(final_path, fps=24)
    return final_path

# ===== Upload Function =====
def upload_video():
    youtube = get_youtube_service()
    video_path = generate_video()

    title = f"{get_random_prompt()} #{random.randint(1000,9999)}"
    description = "Auto-generated motivational & lifestyle shorts. Stay inspired!"
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["motivation", "shorts", "inspiration", "life"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print("✅ Uploaded:", response.get("id"))

    os.remove(video_path)
    os.remove("temp.jpg")

# ===== Scheduler =====
schedule.every(5).hours.do(upload_video)

print("🚀 Auto YouTube Upload started... (every 5 hours)")
while True:
    schedule.run_pending()
    time.sleep(60)
    
