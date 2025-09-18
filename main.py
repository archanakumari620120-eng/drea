import os
import random
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import textwrap
import yt_dlp

# ------------------ Config ------------------
IMAGES_DIR = "images"
VIDEOS_DIR = "videos"
QUOTES_FILE = "quotes.txt"

VIDEO_DURATION = 12  # seconds
VIDEO_SIZE = (1080, 1920)
FONT_FILE = "arial.ttf"  # PIL font
MAX_FONT_SIZE = 100
MIN_FONT_SIZE = 40

# Env variables for secrets
TOKEN_FILE = os.environ.get("TOKEN_FILE", "token.json")
CLIENT_SECRET_FILE = os.environ.get("CLIENT_SECRET_FILE", "client_secret.json")
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ------------------ Helpers ------------------
def load_quotes():
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def generate_image(prompt, output_path):
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
    )
    pipe.to("cuda" if torch.cuda.is_available() else "cpu")
    image = pipe(prompt).images[0]
    image.save(output_path)
    return output_path

def overlay_text_on_image(image_path, text, output_path):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_size = MAX_FONT_SIZE
    max_width = img.width - 100
    max_height = img.height - 200

    while font_size >= MIN_FONT_SIZE:
        font = ImageFont.truetype(FONT_FILE, font_size)
        lines = textwrap.wrap(text, width=25)
        line_heights = [draw.textsize(line, font=font)[1] for line in lines]
        total_height = sum(line_heights) + 10*(len(lines)-1)
        if total_height <= max_height:
            break
        font_size -= 2

    # Semi-transparent rectangle for readability
    rectangle_height = total_height + 40
    rectangle_y = (img.height - rectangle_height)//2
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(50, rectangle_y), (img.width-50, rectangle_y+rectangle_height)],
        fill=(0,0,0,120)
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    y_text = rectangle_y + 20
    for line in lines:
        w, h = draw.textsize(line, font=font)
        x_text = (img.width - w)/2
        draw.text(
            (x_text, y_text),
            line,
            font=font,
            fill="white",
            stroke_width=2,
            stroke_fill="black"
        )
        y_text += h + 10

    img.convert("RGB").save(output_path)
    return output_path

def download_copyright_free_music():
    """Download random copyright-free music from YouTube."""
    search_query = "motivational background music copyright free"
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": os.path.join("music_temp", "%(id)s.%(ext)s")
    }
    os.makedirs("music_temp", exist_ok=True)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
        file_path = ydl.prepare_filename(info["entries"][0])
    return file_path

def create_video(image_path, music_path, output_path):
    clip = ImageClip(image_path).set_duration(VIDEO_DURATION).resize(VIDEO_SIZE)
    if music_path:
        audio = AudioFileClip(music_path).subclip(0, VIDEO_DURATION)
        clip = clip.set_audio(audio)
    clip.write_videofile(output_path, fps=24)
    clip.close()

def youtube_upload(video_file, title, description="", tags=[]):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, YOUTUBE_SCOPES)
    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "tags": tags},
            "status": {"privacyStatus": "public"},
        },
        media_body=video_file
    )
    response = request.execute()
    return response

# ------------------ Main ------------------
def main():
    quotes = load_quotes()
    for quote in quotes:  # Single run per workflow
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(IMAGES_DIR, f"{timestamp}.jpg")
            text_image_path = os.path.join(IMAGES_DIR, f"{timestamp}_text.jpg")
            video_path = os.path.join(VIDEOS_DIR, f"{timestamp}.mp4")

            # Generate image
            prompt = f"{quote}, highly aesthetic, motivational, trending style, vibrant colors, sharp focus"
            generate_image(prompt, image_path)

            # Overlay text
            overlay_text_on_image(image_path, quote, text_image_path)

            # Download music
            music_path = download_copyright_free_music()

            # Create video
            create_video(text_image_path, music_path, video_path)

            # Upload
            youtube_upload(video_path, title=quote, description="Motivational Short", tags=["motivation","shorts"])

            # Cleanup
            os.remove(image_path)
            os.remove(text_image_path)
            os.remove(video_path)
            os.remove(music_path)

            print("✅ Video uploaded successfully.")

        except Exception as e:
            print("❌ Error:", e)

if __name__ == "__main__":
    main()
        
