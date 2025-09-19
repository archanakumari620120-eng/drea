import os
import random
import yt_dlp
import torch
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip
from diffusers import StableDiffusionPipeline
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 📂 Directories
IMAGES_DIR = "images"
MUSIC_DIR = "music"
VIDEOS_DIR = "videos"
QUOTES_FILE = "quotes.txt"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# 🎯 Config
video_duration = 15
topic = "Motivational Quotes"
playlist_url = "https://www.youtube.com/playlist?list=PLzCxunOM5WFLvFj8k1nKQw0h0lMftzG0q"

# 🤖 AI pipeline (CPU safe)
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to(device)

# 📝 Load quotes
def load_quotes():
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return ["Stay motivated!", "Keep going!", "Never give up!"]

# 🖼️ Generate AI/fallback image with text
def generate_image(i, quote):
    try:
        prompt = f"cinematic motivational wallpaper, {topic}, Indian style, 4k, ultra realistic"
        result = pipe(prompt, height=720, width=1280, num_inference_steps=20)
        image = result.images[0] if result and hasattr(result, "images") else None
        if image is None:
            raise ValueError("AI image gen failed")
    except Exception as e:
        print(f"⚠️ AI Image gen failed: {e}")
        image = Image.new("RGB", (1280, 720), color=(0, 0, 0))

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
    except:
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(quote, font=font)
    x, y = (image.width - text_w) // 2, (image.height - text_h) // 2
    draw.text((x, y), quote, font=font, fill=(255, 255, 255))

    path = os.path.join(IMAGES_DIR, f"image_{i}.png")
    image.save(path)
    return path

# 🎵 Get or download music
def get_music():
    try:
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        if not files:
            ydl_opts = {
                "format": "bestaudio/best",
                "extractaudio": True,
                "audioformat": "mp3",
                "outtmpl": os.path.join(MUSIC_DIR, "%(title)s.%(ext)s"),
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([playlist_url])
            files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        return os.path.join(MUSIC_DIR, random.choice(files)) if files else None
    except Exception as e:
        print(f"⚠️ Music failed: {e}")
        return None

# 🎬 Make video
def create_video(i, img, audio):
    try:
        path = os.path.join(VIDEOS_DIR, f"video_{i}.mp4")
        clip = ImageClip(img, duration=video_duration)
        if audio and os.path.exists(audio):
            audio_clip = AudioFileClip(audio).subclip(0, video_duration)
            clip = clip.set_audio(audio_clip)
        else:
            print("⚠️ No audio, silent video.")
        clip.write_videofile(path, fps=24, codec="libx264", audio_codec="aac")
        return path
    except Exception as e:
        print(f"❌ Video failed: {e}")
        return None

# ⬆️ Upload to YouTube
def upload_video(video_path, title, description, tags):
    try:
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "22"  # People & Blogs
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=video_path
        )
        response = request.execute()
        print(f"✅ Uploaded: https://youtu.be/{response['id']}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

# 🚀 Main
def run_automation(total_videos=1):
    quotes = load_quotes()
    for i in range(total_videos):
        quote = random.choice(quotes)
        print(f"\n🎬 Making video {i} with: {quote}")
        img = generate_image(i, quote)
        audio = get_music()
        video = create_video(i, img, audio)

        if video:
            title = f"{quote} | Motivational Shorts"
            description = f"{quote}\n\nStay motivated daily with powerful life lessons."
            tags = ["motivation", "life", "success", "shorts", "inspiration"]
            upload_video(video, title, description, tags)
        else:
            print(f"❌ Video {i} failed")

    print("\n🎉 Automation completed!")

if __name__ == "__main__":
    run_automation(total_videos=1)
        
