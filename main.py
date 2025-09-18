import os
import random
import yt_dlp
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image, ImageDraw
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

# 🤖 AI pipeline
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
).to(device)

# ✅ Quotes list
quotes = [
    "Believe you can and you're halfway there. — Theodore Roosevelt",
    "No pressure, no diamonds. — Thomas Carlyle",
    "The purpose of our lives is to be happy. — Dalai Lama",
    "Life isn’t about finding yourself. It’s about creating yourself. — George Bernard Shaw",
    "Stay foolish, stay hungry. — Steve Jobs",
    "Do what you can, with what you have, where you are. — Theodore Roosevelt",
    "Keep smiling because life is a beautiful thing and there’s so much to smile about. — Marilyn Monroe",
    "It always seems impossible until it’s done. — Nelson Mandela",
    # agar chahe to aur quotes add karo
]

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

# 🖼️ Helpers

def resize_image_with_lanczos(img_path, target_w, target_h, i):
    """
    Resize the image to fit within (target_w, target_h) maintaining aspect ratio,
    using high-quality resampling (LANCZOS), to avoid edge cutting and quality loss.
    Returns path of resized image.
    """
    # Open with PIL
    img = Image.open(img_path).convert("RGB")
    img_w, img_h = img.size

    # Compute scaling ratio
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    # Use LANCZOS or Resampling.LANCZOS depending on pillow version
    try:
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    except AttributeError:
        resized = img.resize((new_w, new_h), Image.LANCZOS)

    resized_path = os.path.join(IMAGES_DIR, f"resized_{i}.png")
    resized.save(resized_path)
    return resized_path

# 🖼️ Image generation with fallback and proper resizing
def generate_image(i):
    try:
        prompt = f"Beautiful high resolution background for {topic}"
        result = pipe(prompt, height=768, width=768, num_inference_steps=25)
        if result and hasattr(result, "images") and len(result.images) > 0:
            image = result.images[0]
        else:
            raise ValueError("No image from diffusion pipeline")
        path = os.path.join(IMAGES_DIR, f"sd_image_{i}.png")
        image.save(path)
        return path
    except Exception as e:
        print(f"⚠️ Image generation failed: {e}")
        fallback = Image.new("RGB", (1080, 1920), color=(30, 30, 30))
        draw = ImageDraw.Draw(fallback)
        fallback_path = os.path.join(IMAGES_DIR, f"fallback_sd_{i}.jpg")
        fallback.save(fallback_path)
        return fallback_path

# 🎬 Video creation (with quote overlay, no text cut, clear)
def create_video(i, img_path, audio_path, quote_text):
    try:
        video_path = os.path.join(VIDEOS_DIR, f"video_{i}.mp4")
        target_w, target_h = 1080, 1920  # video resolution (vertical)

        # First, generate or get image
        # Resize it properly to avoid cutting
        resized_img_path = resize_image_with_lanczos(img_path, target_w, target_h, i)

        # Make clip from resized image
        clip = ImageClip(resized_img_path).set_duration(video_duration)

        # Create black background
        from moviepy.video.fx.all import margin
        bg = ImageClip(color=(0,0,0), size=(target_w, target_h)).set_duration(video_duration)
        clip = clip.set_position(("center","center"))
        final_img_clip = CompositeVideoClip([bg, clip])

        # Slight dark overlay for text clarity
        final_img_clip = final_img_clip.fl_image(lambda frame: (frame * 0.8).astype('uint8'))

        # Text overlay
        txt = (TextClip(
                    quote_text,
                    fontsize=70,
                    font="Arial-Bold",  # ya tumhare machine pe installed font
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(int(target_w * 0.8), None),  # text width 80%
                    align='center'
                )
               .set_position(('center', 'bottom'))
               .set_duration(video_duration)
               .margin(bottom=100)
              )

        video = CompositeVideoClip([final_img_clip, txt])

        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path).volumex(0.5)
            video = video.set_audio(audio_clip)

        video.write_videofile(
            video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            ffmpeg_params=["-crf", "20"]
        )
        print("✅ Video created:", video_path)
        return video_path
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return None

# 📤 YouTube Upload parts (as before)
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

# 🚀 Main automation
def run_automation(total_videos=1):
    for i in range(total_videos):
        print(f"\n🎬 Creating video {i}")
        img = generate_image(i)
        music = get_music()
        quote = random.choice(quotes)
        video = create_video(i, img, music, quote)
        if video:
            print(f"✅ Video {i} done: {video}")
            upload_to_youtube(video, i)
        else:
            print(f"❌ Video {i} failed")
    print("\n🎉 Automation completed!")

if __name__ == "__main__":
    run_automation(total_videos=1)
    
