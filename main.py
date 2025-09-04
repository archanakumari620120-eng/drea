import os
import time
import random
import schedule
from moviepy.editor import ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# ===============================
# YOUTUBE API AUTH
# ===============================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=8081)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

# ===============================
# VIDEO GENERATION
# ===============================
def create_text_image(text, size=(1080, 1920), fontsize=70, font_color="white", bg_color="black"):
    img = Image.new("RGB", size, color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except:
        font = ImageFont.load_default()

    w, h = draw.textsize(text, font=font)
    pos = ((size[0] - w) // 2, (size[1] - h) // 2)
    draw.text(pos, text, font=font, fill=font_color)

    img_path = "text.png"
    img.save(img_path)
    return img_path


def generate_video(output_file="output.mp4"):
    print("🎬 Generating video...")

    texts = [
        "Stay motivated 💪",
        "Keep learning 📚",
        "Success needs patience 🚀",
        "Dream big 🌟",
        "Never give up 🔥"
    ]
    text_img = create_text_image(random.choice(texts), fontsize=80)

    clip = ImageClip(text_img).set_duration(10)
    final = CompositeVideoClip([clip])

    final.write_videofile(output_file, fps=30, codec="libx264", audio=False)
    print("✅ Video generated:", output_file)
    return output_file

# ===============================
# YOUTUBE UPLOAD
# ===============================
def upload_video(youtube, file):
    print(f"📤 Uploading {file} to YouTube...")

    titles = [
        "🔥 Motivational Shorts",
        "🚀 Daily Inspiration",
        "💡 Success Tips",
        "🌟 Keep Going",
        "💪 Hard Work Pays Off"
    ]
    descriptions = [
        "Never give up. Keep pushing forward! 💯",
        "Your daily dose of motivation 🚀",
        "Inspiration to achieve your dreams 🌟",
        "Shorts that boost your mindset 💡",
        "Stay strong, stay motivated 💪"
    ]

    body = {
        "snippet": {
            "title": random.choice(titles),
            "description": random.choice(descriptions),
            "tags": ["motivation", "shorts", "success", "inspiration"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(file, chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"⏳ Uploading... {int(status.progress() * 100)}%")

    print("✅ Upload complete! Video ID:", response["id"])

# ===============================
# JOB
# ===============================
def job():
    print("🚀 Job started...")
    youtube = get_youtube_service()

    video_file = generate_video()
    upload_video(youtube, video_file)

    os.remove(video_file)
    if os.path.exists("text.png"):
        os.remove("text.png")

    print("🗑️ Temporary files cleaned.")

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    print("✅ Script started...")

    # Run once immediately for testing
    job()

    # Then repeat every 5 hours
    schedule.every(5).hours.do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)
            
