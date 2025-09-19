import os
import random
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image, ImageDraw
from yt_dlp import YoutubeDL
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 📂 Directories
IMAGES_DIR = "images"
MUSIC_DIR = "music"
VIDEOS_DIR = "videos"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# 🎯 Video config
video_duration = 12
topic = "Motivational Quotes"

# 🤖 AI pipeline setup (CPU safe)
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to(device)

# 🎵 Royalty free playlist (changeable)
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLzCxunOM5WFI6H2k8zJpE7E5Wdl66iRSu"

# 📜 Load quotes
def load_quotes():
    if os.path.exists("quotes.txt"):
        with open("quotes.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return ["Stay motivated!", "Keep going, success is near!"]

QUOTES = load_quotes()

# 🎵 Download random free music
def download_random_music():
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'outtmpl': os.path.join(MUSIC_DIR, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(PLAYLIST_URL, download=False)
            entries = info.get("entries", [])
            if not entries:
                return None

            choice = random.choice(entries)
            print(f"🎵 Downloading: {choice['title']}")
            ydl.download([choice["webpage_url"]])
            path = os.path.join(MUSIC_DIR, f"{choice['title']}.mp3")
            return path if os.path.exists(path) else None
    except Exception as e:
        print(f"⚠️ Music download failed: {e}")
        return None

# 🖼️ Image generation
def generate_image(i, quote):
    try:
        prompt = f"Ultra realistic cinematic background for {topic}, theme: {quote}, trending, powerful"
        result = pipe(prompt, height=720, width=1280, num_inference_steps=20)

        if result and hasattr(result, "images") and len(result.images) > 0:
            image = result.images[0]
        else:
            raise ValueError("No image from diffusion pipeline")

        path = os.path.join(IMAGES_DIR, f"image_{i}.png")
        image.save(path)
        return path

    except Exception as e:
        print(f"⚠️ Image generation failed for {i}, fallback used: {e}")
        fallback = Image.new("RGB", (1280, 720), color=(0, 0, 0))
        d = ImageDraw.Draw(fallback)
        d.text((50, 360), f"{quote}", fill=(255, 255, 255))
        path = os.path.join(IMAGES_DIR, f"image_fallback_{i}.png")
        fallback.save(path)
        return path

# 🎬 Video creation
def create_video(i, img, audio, quote):
    try:
        path = os.path.join(VIDEOS_DIR, f"video_{i}.mp4")
        clip = ImageClip(img, duration=video_duration)

        # Add text overlay
        txt = TextClip(quote, fontsize=60, color="white", font="Arial-Bold", method="caption", size=(1000, None))
        txt = txt.set_position("center").set_duration(video_duration)

        final = CompositeVideoClip([clip, txt])

        if audio and os.path.exists(audio):
            audio_clip = AudioFileClip(audio).subclip(0, video_duration)
            final = final.set_audio(audio_clip)
        else:
            print(f"⚠️ No audio for video {i}, silent video.")

        final.write_videofile(path, fps=24, codec="libx264", audio_codec="aac")
        return path

    except Exception as e:
        print(f"❌ Video creation failed for {i}: {e}")
        return None

# 📤 YouTube Upload
def upload_to_youtube(video_path, title, description, tags):
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
                "status": {
                    "privacyStatus": "public",
                },
            },
            media_body=video_path
        )
        response = request.execute()
        print(f"✅ Uploaded to YouTube: https://youtu.be/{response['id']}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

# 🚀 Main automation
def run_automation(total_videos=1):
    for i in range(total_videos):
        print(f"\n🎬 Starting video {i}")
        quote = random.choice(QUOTES)
        img = generate_image(i, quote)
        audio = download_random_music()
        video = create_video(i, img, audio, quote)

        if video:
            title = f"{quote[:60]} | Motivational Shorts"
            description = f"{quote}\n\n#motivation #inspiration #shorts"
            tags = ["motivation", "life", "success", "shorts", "inspiration"]
            upload_to_youtube(video, title, description, tags)
            print(f"✅ Video {i} ready and uploaded")
        else:
            print(f"❌ Video {i} failed")

    print("\n🎉 Automation completed!")

if __name__ == "__main__":
    run_automation(total_videos=1)
        
