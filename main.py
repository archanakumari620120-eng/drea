import os
import random
import traceback
import requests
import json
from time import sleep

# Video processing
from moviepy.editor import ImageClip, AudioFileClip, vfx, CompositeVideoClip

# YouTube API
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Gemini API
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
# FIX: Import the specific exception for better error handling
from google.api_core import exceptions as google_exceptions

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

# ---------------- GEMINI: Concept, Title, Description, Tags ----------------
def generate_concept_and_metadata():
    """Generates video metadata using a more common model for debugging."""
    try:
        print("🔹 Generating metadata with Gemini...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        generation_config = GenerationConfig(response_mime_type="application/json")
        
        # FIX: Switched to a more universally available model ('gemini-pro') for troubleshooting.
        # If this works, the problem is access to the '1.5-flash' model.
        print("--- DEBUG: Trying model 'gemini-pro' ---")
        model = genai.GenerativeModel(
            'gemini-pro',
            generation_config=generation_config
        )

        categories = ["Animal", "Human", "Boy", "Girl", "Sport", "Space", "Nature", "Motivation", "Quotes"]
        category = random.choice(categories)

        user_prompt = f"""
        You are a YouTube Shorts content expert. Generate viral content ideas.
        Your output MUST be a single, clean JSON object.
        Category: {category}
        JSON format:
        {{
            "concept": "A very short, creative, and visually compelling concept for an AI image.",
            "title": "A catchy, viral YouTube Shorts title (under 70 characters).",
            "description": "A short description with 3-4 relevant hashtags at the end.",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
            "category": "{category}"
        }}
        """
        
        response = model.generate_content(user_prompt)
        metadata = json.loads(response.text)
        print("✅ Gemini metadata generated successfully.")
        return metadata

    # FIX: Added specific error handling to give better advice.
    except google_exceptions.PermissionDenied as e:
        print("\n❌ GEMINI PERMISSION DENIED: Your API key or Google Cloud project does not have permission.")
        print("   Please check the following:")
        print("   1. Is the Vertex AI API enabled in your Google Cloud project?")
        print("   2. Is your API key correct and active?")
        print(f"   Original error: {e}")
        raise
    except google_exceptions.NotFound as e:
        print(f"\n❌ GEMINI MODEL NOT FOUND: The model 'gemini-pro' was not found.")
        print("   This is highly unusual and points to a fundamental issue with your API key or project setup.")
        print(f"   Original error: {e}")
        raise
    except Exception as e:
        print(f"❌ Gemini metadata error: {e}")
        traceback.print_exc()
        raise

# ... The rest of your code (generate_image_huggingface, create_video, etc.) remains the same ...
# (The functions below are unchanged from the previous version)

# ---------------- HUGGING FACE IMAGE GENERATION ----------------
def generate_image_huggingface(prompt, model_id="stabilityai/stable-diffusion-xl-base-1.0"):
    API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": f"{prompt}, cinematic, high detail, trending on artstation, vibrant colors",
        "parameters": { "width": 1080, "height": 1920, "negative_prompt": "blurry, deformed, ugly, watermark, text" }
    }
    print(f"🖼️ Requesting image from Hugging Face for prompt: {prompt}")
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 503:
        print("⏳ Model is loading, waiting for 30 seconds...")
        sleep(30)
        response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Hugging Face API error {response.status_code}: {response.text}")
    img_path = os.path.join(VIDEOS_DIR, "frame.png")
    with open(img_path, "wb") as f: f.write(response.content)
    print(f"✅ Image saved successfully: {img_path}")
    return img_path

# ---------------- MUSIC SELECTION ----------------
def get_random_music():
    try:
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith((".mp3", ".wav", ".m4a"))]
        if not files:
            print("⚠️ No music found. The video will be silent.")
            return None
        chosen = os.path.join(MUSIC_DIR, random.choice(files))
        print(f"🎵 Music selected: {chosen}")
        return chosen
    except Exception as e:
        print(f"❌ Error selecting music: {e}"); raise

# ---------------- VIDEO CREATION ----------------
def create_video(image_path, audio_path, output_path="final_video.mp4"):
    try:
        print("🎬 Creating video with zoom effect...")
        clip_duration = 10
        clip = (ImageClip(image_path).set_duration(clip_duration).resize(lambda t: 1 + 0.02 * t).set_position(('center', 'center')))
        final_clip = CompositeVideoClip([clip], size=(1080, 1920))
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration < clip_duration:
                audio_clip = audio_clip.fx(vfx.loop, duration=clip_duration)
            final_clip = final_clip.set_audio(audio_clip.subclip(0, clip_duration))
        final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Video created successfully: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Video creation error: {e}"); traceback.print_exc(); raise

# ---------------- YOUTUBE UPLOAD ----------------
def upload_to_youtube(video_path, title, description, tags, category_name, privacy="public"):
    try:
        print("📤 Uploading to YouTube...")
        token_info = json.loads(TOKEN_JSON)
        creds = Credentials.from_authorized_user_info(token_info, scopes=["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)
        category_map = { "Animal": "15", "Sport": "17", "Space": "28", "Nature": "15", "Motivation": "22", "Quotes": "22", "Human": "22", "Boy": "22", "Girl": "22" }
        category_id = category_map.get(category_name, "22")
        request_body = {
            "snippet": { "title": title, "description": description, "tags": tags, "categoryId": category_id },
            "status": { "privacyStatus": privacy, "selfDeclaredMadeForKids": False }
        }
        print(f"🚀 Sending video upload request with category '{category_name}' ({category_id})...")
        request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=video_path)
        response = request.execute()
        print(f"✅ Video uploaded successfully! Video ID: {response.get('id')}")
        return response.get("id")
    except Exception as e:
        print(f"❌ YouTube upload error: {e}"); traceback.print_exc(); raise

# ---------------- MAIN PIPELINE ----------------
if __name__ == "__main__":
    try:
        metadata = generate_concept_and_metadata()
        img_path = generate_image_huggingface(metadata["concept"])
        music_path = get_random_music()
        video_path = create_video(img_path, music_path)
        upload_to_youtube(video_path, metadata["title"], metadata["description"], metadata["tags"], metadata["category"])
        print("\n🎉 Pipeline completed successfully! 🎉")
    except Exception as e:
        print(f"\n❌ Pipeline failed.")
        
