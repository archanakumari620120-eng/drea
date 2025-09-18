import os
import random
import yt_dlp
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from datetime import datetime
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 📂 Directories
IMAGES_DIR = "images"
MUSIC_DIR = "music"
VIDEOS_DIR = "videos"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# 🎯 Config
video_duration = 10
topic = "Motivational Quotes"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ✅ Quotes list from file
def load_quotes():
    if os.path.exists("quotes.txt"):
        with open("quotes.txt", "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]
        return quotes
    return ["Stay positive and keep going!"]

quotes = load_quotes()

# 🎵 Music download
def download_music():
    url = "https://www.youtube.com/watch?v=2OEL4P1Rz04"
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(MUSIC_DIR, "music.%(ext)s"),
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    try:
        yt_dlp.YoutubeDL(ydl_opts).download([url])
        print("✅ Downloaded music")
    except Exception as e:
        print(f"⚠️ Music download failed: {e}")

def get_music():
    files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(".mp3")]
    if not files:
        download_music()
        files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(".mp3")]
    if files:
        return os.path.join(MUSIC_DIR, random.choice(files))
    return None

# 🖼️ Image fallback (black bg if no AI)
def generate_image(i):
    path = os.path.join(IMAGES_DIR, f"bg_{i}.jpg")
    img = Image.new("RGB", (1080, 1920), color=(20, 20, 20))
    img.save(path)
    return path

# 📝 PIL-based text rendering (no ImageMagick needed)
def make_text_image(text, size=(1080, 1920), font_size=60):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Word wrap
    max_width = size[0] - 100
    lines = []
    words = text.split()
    line = ""
    for word in words:
        test_line = line + " " + word if line else word
        w, _ = draw.textsize(test_line, font=font)
        if w <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    # Position center
    total_h = sum(draw.textsize(l, font=font)[1] + 10 for l in lines)
    y = (size[1] - total_h) // 2

    for l in lines:
        w, h = draw.textsize(l, font=font)
        x = (size[0] - w) // 2
        draw.text((x, y), l, font=font, fill="white", stroke_fill="black", stroke_width=2)
        y += h + 10

    return np.array(img)

# 🎬 Video creation
def create_video(i, img_path, audio_path, quote_text):
    try:
        video_path = os.path.join(VIDEOS_DIR, f"video_{i}.mp4")

        bg_clip = ImageClip(img_path).set_duration(video_duration).resize((1080, 1920))

        txt_img = make_text_image(quote_text, size=(1080, 1920), font_size=70)
        txt_clip = ImageClip(txt_img, transparent=True).set_duration(video_duration)

        video = CompositeVideoClip([bg_clip, txt_clip])

        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path).volumex(0.5)
            video = video.set_audio(audio_clip)

        video.write_videofile(video_path, fps=24, codec="libx264", audio_codec="aac",
                              preset="medium", threads=4, ffmpeg_params=["-crf", "20"])
        print("✅ Video created:", video_path)
        return video_path
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return None

# 📤 YouTube Upload
def get_youtube_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=8081)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(video_path, i):
    try:
        youtube = get_youtube_service()
        title = f"{topic} #{i}"
        description = f"Auto-generated YouTube Shorts about {topic}.\nUploaded via automation."
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["Motivation", "Shorts", "AI Generated"],
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=video_path
        )
        response = request.execute()
        print(f"✅ Uploaded to YouTube: https://youtu.be/{response['id']}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

# 🚀 Main
def run_automation(total_videos=1):
    for i in range(total_videos):
        print(f"\n🎬 Creating video {i}")
        img = generate_image(i)
        music = get_music()
        quote = random.choice(quotes)
        video = create_video(i, img, music, quote)
        if video:
            upload_to_youtube(video, i)
        else:
            print(f"❌ Video {i} failed")
    print("\n🎉 Automation completed!")

if __name__ == "__main__":
    run_automation(total_videos=1)
    
