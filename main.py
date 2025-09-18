import os
import random
import yt_dlp
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image, ImageDraw
import textwrap
from datetime import datetime
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------------- Directories ----------------
IMAGES_DIR = "images"
MUSIC_DIR = "music"
VIDEOS_DIR = "videos"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# ---------------- Config ----------------
video_duration = 10
topic = "Motivational Quotes"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ---------------- AI Pipeline ----------------
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to(device)

# ---------------- Quotes ----------------
quotes_file = "quotes.txt"
if os.path.exists(quotes_file):
    with open(quotes_file, "r", encoding="utf-8") as f:
        quotes_list = [line.strip() for line in f if line.strip()]
else:
    quotes_list = [
        "Success is not final, failure is not fatal: It is the courage to continue that counts.",
        "The only limit to our realization of tomorrow is our doubts of today.",
        "Believe you can and you're halfway there."
    ]

# ---------------- Image Generation ----------------
def generate_image(i):
    try:
        prompt = f"Viral YouTube Short image about {topic}"
        result = pipe(prompt, height=1080, width=1920, num_inference_steps=20)
        if result and hasattr(result, "images") and len(result.images) > 0:
            image = result.images[0]
        else:
            raise ValueError("No image from diffusion pipeline")
        path = os.path.join(IMAGES_DIR, f"image_{i}.png")
        image.save(path)
        return path
    except Exception as e:
        print(f"⚠️ Image generation failed: {e}")
        fallback = Image.new("RGB", (1080, 1920), color=(0, 0, 0))
        d = ImageDraw.Draw(fallback)
        d.text((50, 960), f"Video {i} - {topic}", fill=(255, 255, 255))
        path = os.path.join(IMAGES_DIR, f"image_fallback_{i}.png")
        fallback.save(path)
        return path

# ---------------- Music ----------------
def download_music():
    url = "https://www.youtube.com/watch?v=2OEL4P1Rz04"  # copyright free example
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
        print("✅ Downloaded copyright free music")
    except Exception as e:
        print(f"⚠️ Music download failed: {e}")

def get_music():
    files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
    if not files:
        download_music()
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
    if files:
        return os.path.join(MUSIC_DIR, random.choice(files))
    return None

# ---------------- Video Creation ----------------
def create_video(i, img_path, quote, audio_path):
    try:
        # Wrap text for better visibility
        wrapped_text = "\n".join(textwrap.wrap(quote, width=25))

        # Text Clip
        txt_clip = TextClip(
            wrapped_text,
            fontsize=70,
            font='Arial-Bold',
            color='white',
            method='caption',
            size=(1080-100, None)
        ).set_position("center").set_duration(video_duration)

        # Image Clip
        img_clip = ImageClip(img_path).set_duration(video_duration)

        # Combine
        final_clip = CompositeVideoClip([img_clip, txt_clip])

        # Add audio if available
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path).volumex(0.6)
            final_clip = final_clip.set_audio(audio_clip)

        # Save video
        video_path = os.path.join(VIDEOS_DIR, f"video_{i}.mp4")
        final_clip.write_videofile(video_path, fps=24, codec="libx264", audio_codec="aac")
        return video_path
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return None

# ---------------- YouTube Upload ----------------
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

# ---------------- Main Automation ----------------
def run_automation(total_videos=1):
    for i in range(total_videos):
        print(f"\n🎬 Starting video {i}")
        img = generate_image(i)
        quote = random.choice(quotes_list)
        audio = get_music()
        video = create_video(i, img, quote, audio)
        if video:
            print(f"✅ Video {i} created at {video}")
            upload_to_youtube(video, i)
        else:
            print(f"❌ Video {i} failed")
    print("\n🎉 Automation completed!")

# ---------------- Run ----------------
if __name__ == "__main__":
    run_automation(total_videos=3)
      
