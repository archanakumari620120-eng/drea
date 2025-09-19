import os
import random
import traceback
import json
from time import sleep
from pathlib import Path

import requests
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip

# Gemini AI
import google.generativeai as genai

# YouTube API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------------- DIRECTORIES ----------------
VIDEOS_DIR = "videos"
MUSIC_DIR = "music"
Path(VIDEOS_DIR).mkdir(exist_ok=True)
Path(MUSIC_DIR).mkdir(exist_ok=True)

# ---------------- SECRETS CHECK ----------------
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TOKEN_JSON = os.getenv("TOKEN_JSON")

if not HF_API_TOKEN or not GEMINI_API_KEY or not TOKEN_JSON:
    raise ValueError("❌ Missing secrets! Check HF_API_TOKEN, GEMINI_API_KEY, TOKEN_JSON")
else:
    print("✅ All secrets loaded")

# ---------------- GEMINI CONFIG ----------------
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-1.5-flash"

# ---------------- FUNCTIONS ----------------

def generate_concept_and_metadata():
    """
    Gemini AI se prompt, title, description, tags, hashtags generate karega.
    Har run me alag content.
    """
    user_prompt = """
    Generate a trending viral YouTube Shorts video metadata.
    Include:
    1. Concept/prompt for image/video (1080x1920 vertical)
    2. Video title
    3. Description
    4. Tags (comma separated)
    5. Hashtags (space separated)

    Content categories: animal, human, boy, girl, sports, space, nature, motivation, quotes
    Make every run unique and viral
    Output in JSON:
    {"prompt": "...", "title": "...", "description": "...", "tags": "...", "hashtags": "..."}
    """
    try:
        response = genai.chat(messages=[{"content": user_prompt}])
        text_output = response.last
        data = json.loads(text_output)
        print("✅ Gemini generated metadata")
        return data
    except Exception as e:
        print(f"❌ Error generating metadata: {e}")
        traceback.print_exc()
        # fallback static concept
        return {
            "prompt": "Vertical 1080x1920 YouTube Short background of Animal Video, ultra-realistic cinematic, trending on YouTube Shorts",
            "title": "Animal Video #Shorts",
            "description": "AI Generated Viral Short",
            "tags": "AI,Shorts,Animals",
            "hashtags": "#AI #Shorts #Animals"
        }

def generate_image(prompt):
    """ Hugging Face text-to-image """
    url = f"https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}
    try:
        print(f"🔹 Hugging Face API request...")
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"HF API Error: {response.status_code}")
        img_path = os.path.join(VIDEOS_DIR, "frame.png")
        with open(img_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Image saved: {img_path}")
        return img_path
    except Exception as e:
        print(f"❌ HF image generation failed: {e}")
        traceback.print_exc()
        # fallback image
        return None

def get_random_music():
    """ Copyright-free YouTube music fetch placeholder """
    try:
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith((".mp3", ".wav"))]
        if not files:
            print("⚠️ No music found, video will be silent.")
            return None
        chosen = os.path.join(MUSIC_DIR, random.choice(files))
        print(f"🎵 Music chosen: {chosen}")
        return chosen
    except Exception as e:
        print(f"❌ Music selection error: {e}")
        return None

def create_video(image_path, audio_path, output_path="final_video.mp4", duration=10):
    """ MoviePy video creation """
    try:
        clip = ImageClip(image_path).set_duration(duration)
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration < duration:
                audio_clip = audio_clip.fx(vfx.loop, duration=duration)
            clip = clip.set_audio(audio_clip.subclip(0, duration))
        clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Video ready: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        traceback.print_exc()
        raise

def upload_to_youtube(video_path, title, description, tags):
    """ YouTube public upload """
    try:
        creds_dict = json.loads(TOKEN_JSON)
        creds = Credentials.from_authorized_user_info(creds_dict, ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags.split(","),
                    "categoryId": "22"
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=video_path
        )
        response = request.execute()
        print(f"✅ Uploaded! Video ID: {response.get('id')}")
        return response.get("id")
    except Exception as e:
        print(f"❌ YouTube upload error: {e}")
        traceback.print_exc()
        raise

# ---------------- MAIN PIPELINE ----------------
if __name__ == "__main__":
    try:
        # 1️⃣ Gemini generates concept, title, description, tags, hashtags
        metadata = generate_concept_and_metadata()
        prompt = metadata.get("prompt")
        title = metadata.get("title")
        description = metadata.get("description")
        tags = metadata.get("tags")

        # 2️⃣ Generate image from HF
        image_path = generate_image(prompt)
        if not image_path:
            print("⚠️ Falling back to default image")
            image_path = "fallback.png"  # Make sure you have a fallback image

        # 3️⃣ Pick music
        music_path = get_random_music()

        # 4️⃣ Create video
        video_path = create_video(image_path, music_path)

        # 5️⃣ Upload to YouTube
        upload_to_youtube(video_path, title=title, description=description, tags=tags)

        print("🎉 Pipeline complete!")

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        traceback.print_exc()
        
