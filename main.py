import os
import json
import random
import traceback
from time import sleep
from moviepy.editor import VideoFileClip, AudioFileClip, vfx
import requests
import google.generativeai as genai
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------------- DIRECTORIES ----------------
VIDEOS_DIR = "videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)

# ---------------- LOAD SECRETS ----------------
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TOKEN_JSON = os.getenv("TOKEN_JSON")

if not HF_API_TOKEN or not GEMINI_API_KEY or not TOKEN_JSON:
    raise ValueError("❌ Missing secrets! Check HF_API_TOKEN, GEMINI_API_KEY, TOKEN_JSON")

# Save TOKEN_JSON to file
with open("token.json", "w") as f:
    f.write(TOKEN_JSON)

print("✅ All secrets loaded")

# ---------------- GEMINI: Generate Concept & Metadata ----------------
def generate_concept_and_metadata():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        prompt = (
            "Generate a viral, trending, YouTube Shorts-ready video idea with:\n"
            "- Title (catchy, unique)\n"
            "- Description (viral, engaging)\n"
            "- Tags and hashtags (trending, relevant)\n"
            "- Video prompt (for image/video generation, vertical 1080x1920)\n"
            "Categories: animal, human, sports, space, nature, motivation, facts, quotes.\n"
            "Output JSON format with keys: title, description, tags, hashtags, prompt."
        )
        response = genai.chat(messages=[{"content": prompt}])
        text_output = response.last
        data = json.loads(text_output)
        return data
    except Exception as e:
        print(f"❌ Error generating metadata: {e}")
        traceback.print_exc()
        return {
            "title": "Default AI Video #shorts",
            "description": "Auto-generated video",
            "tags": ["AI", "Shorts"],
            "hashtags": ["#AI", "#Shorts"],
            "prompt": "Vertical 1080x1920 AI background video"
        }

# ---------------- HUGGING FACE: Generate Video ----------------
def generate_video_hf(prompt):
    try:
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {"inputs": prompt, "options":{"wait_for_model":True}}
        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        print(f"📝 Prompt for video: {prompt}")
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"⚠️ Hugging Face API failed, status: {response.status_code}")
            return None
        video_path = os.path.join(VIDEOS_DIR, "final_video.mp4")
        with open(video_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Video saved: {video_path}")
        return video_path
    except Exception as e:
        print(f"❌ Error generating video: {e}")
        traceback.print_exc()
        return None

# ---------------- YOUTUBE UPLOAD ----------------
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
        return None

# ---------------- MAIN PIPELINE ----------------
if __name__ == "__main__":
    try:
        # 1️⃣ Generate metadata
        metadata = generate_concept_and_metadata()

        # 2️⃣ Generate video
        video_path = generate_video_hf(metadata["prompt"])
        if not video_path:
            print("⚠️ Video generation failed. Exiting...")
            exit(1)

        # 3️⃣ Upload to YouTube
        upload_to_youtube(video_path, metadata["title"], metadata["description"], metadata["tags"])

        print("🎉 Pipeline complete!")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        traceback.print_exc()
