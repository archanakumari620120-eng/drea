import os
import random
import traceback
import requests
import json
import re
from time import sleep

from moviepy.editor import ImageClip, AudioFileClip, vfx

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import google.generativeai as genai

# ---------------- CONFIG & DIRECTORIES ----------------
VIDEOS_DIR = "videos"
MUSIC_DIR = "music"
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# ---------------- SECRETS ----------------
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TOKEN_JSON = os.getenv("TOKEN_JSON")

if not all([HF_API_TOKEN, GEMINI_API_KEY, TOKEN_JSON]):
    raise ValueError("❌ Missing one or more secrets! Check HF_API_TOKEN, GEMINI_API_KEY, TOKEN_JSON")
print("✅ All secrets loaded successfully.")

# Configure genai
genai.configure(api_key=GEMINI_API_KEY)

def choose_valid_model(possible_models):
    """
    Among the given list, return the first model that:
     - appears in the list_models()
     - supports generateContent
    """
    print("🔍 Fetching list of available models...")
    available = []
    try:
        for m in genai.list_models():
            available.append(m)
        print(f"Models fetched: {[m.name for m in available]}")
    except Exception as e:
        print("⚠️ Could not list models:", e)
        # fallback: just return first possible
        return possible_models[0]

    for cand in possible_models:
        for m in available:
            if m.name == cand and "generateContent" in getattr(m, "supported_generation_methods", []):
                print(f"✅ Using model: {cand}")
                return cand
    # fallback
    print("⚠️ None of the desired models found; falling back to default:", possible_models[0])
    return possible_models[0]

def generate_concept_and_metadata():
    """Generates video metadata using Gemini API."""
    try:
        print("🔹 Generating metadata with Gemini...")

        # List of models you want to try (in preferred order)
        preferred = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-pro"]
        model_name = choose_valid_model(preferred)

        # Prepare prompt
        categories = ["Animal", "Human", "Boy", "Girl", "Sport", "Space", "Nature", "Motivation", "Quotes"]
        category = random.choice(categories)
        user_prompt = f"""
You are a YouTube Shorts content expert. Generate viral content ideas.
Your output MUST be a single, clean JSON object, without any markdown formatting like ```json.
Category: {category}
JSON format:
{{
    "concept": "A very short, creative, and visually compelling concept for an AI image.",
    "title": "A catchy, viral YouTube Shorts title (under 70 characters).",
    "description": "A short description with 3-4 relevant hashtags at the end.",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}
"""
        # Use new SDK style (Client → models.generate_content) if available
        # But since you're using google.generativeai, use the legacy form:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(user_prompt)
        response_text = resp.text if hasattr(resp, "text") else str(resp)
        # extract JSON
        cleaned = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not cleaned:
            raise ValueError("❌ Gemini did not return a valid JSON object.")
        metadata = json.loads(cleaned.group(0))
        print("✅ Gemini metadata generated successfully.")
        return metadata

    except Exception as e:
        print(f"❌ Gemini metadata error: {e}")
        traceback.print_exc()
        raise

def generate_image_huggingface(prompt, model_id="stabilityai/stable-diffusion-xl-base-1.0"):
    API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": f"Vertical (1080x1920), {prompt}, cinematic, high detail, trending on artstation"}

    print(f"🖼️ Requesting image from Hugging Face for prompt: {prompt}")
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 503:
        print("⏳ Model is loading, waiting for 30 seconds...")
        sleep(30)
        response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Hugging Face API error {response.status_code}: {response.text}")

    img_path = os.path.join(VIDEOS_DIR, "frame.png")
    with open(img_path, "wb") as f:
        f.write(response.content)
    print(f"✅ Image saved successfully: {img_path}")
    return img_path

def get_random_music():
    try:
        files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".wav"))]
        if not files:
            print("⚠️ No music found in the music folder. The video will be silent.")
            return None
        chosen = os.path.join(MUSIC_DIR, random.choice(files))
        print(f"🎵 Music selected: {chosen}")
        return chosen
    except Exception as e:
        print(f"❌ Error selecting music: {e}")
        raise

def create_video(image_path, audio_path, output_path="final_video.mp4"):
    try:
        print("🎬 Creating video...")
        clip_duration = 10
        clip = ImageClip(image_path).set_duration(clip_duration)

        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration < clip_duration:
                audio_clip = audio_clip.fx(vfx.loop, duration=clip_duration)
            clip = clip.set_audio(audio_clip.subclip(0, clip_duration))

        clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Video created successfully: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Video creation error: {e}")
        traceback.print_exc()
        raise

def upload_to_youtube(video_path, title, description, tags, privacy="public"):
    try:
        print("📤 Uploading to YouTube...")
        token_info = json.loads(TOKEN_JSON)
        creds = Credentials.from_authorized_user_info(token_info, scopes=["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)

        request_body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False
            }
        }

        print("🚀 Sending video upload request...")
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=video_path
        )
        response = request.execute()
        print(f"✅ Video uploaded successfully! Video ID: {response.get('id')}")
        return response.get("id")
    except Exception as e:
        print(f"❌ YouTube upload error: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        metadata = generate_concept_and_metadata()
        img_path = generate_image_huggingface(metadata["concept"])
        music_path = get_random_music()
        video_path = create_video(img_path, music_path)
        upload_to_youtube(video_path, metadata["title"], metadata["description"], metadata["tags"])
        print("\n🎉 Pipeline completed successfully! 🎉")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        traceback.print_exc()
    
