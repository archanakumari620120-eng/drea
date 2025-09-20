import os
import json
import requests
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 📂 Directories
VIDEOS_DIR = "videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)

# ✅ Load secrets
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TOKEN_JSON = os.getenv("TOKEN_JSON")

if not HF_API_TOKEN or not GEMINI_API_KEY or not TOKEN_JSON:
    raise ValueError("❌ Missing secrets! Check HF_API_TOKEN, GEMINI_API_KEY, TOKEN_JSON")

print("✅ All secrets loaded")

# 🎯 Gemini Configuration
genai.configure(api_key=GEMINI_API_KEY)

def generate_concept_and_metadata():
    model = genai.GenerativeModel("gemini-1.5-flash")

    user_prompt = """
    You are an expert YouTube Shorts content creator.
    Generate JSON with these fields:
    - title: catchy viral short title
    - description: engaging description (2-3 lines)
    - tags: 10 SEO-optimized tags
    - hashtags: 10 trending hashtags
    - video_prompt: powerful prompt for video generation
    
    Categories must rotate among:
    animals, sports, space, motivation, nature, human emotions, trending topics.
    Every run must produce unique viral content.
    """

    response = model.generate_content(user_prompt)

    try:
        data = json.loads(response.text)
    except:
        data = {
            "title": "Viral YouTube Short",
            "description": response.text[:500],
            "tags": ["viral", "shorts", "trending"],
            "hashtags": ["#viral", "#shorts", "#trending"],
            "video_prompt": "Cinematic vertical video of a trending viral topic"
        }

    return data

# 🎬 HuggingFace Video Generation
def generate_video(prompt, output_path):
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    url = "https://api-inference.huggingface.co/models/cerspense/zeroscope_v2_576w"

    print(f"📝 Prompt for video: {prompt}")
    response = requests.post(url, headers=headers, json={"inputs": prompt})

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Video saved: {output_path}")
        return True
    else:
        print(f"⚠️ Video generation failed, status {response.status_code}")
        return False

# 🎶 Placeholder (no music for now)
def add_background_music(video_path, output_path):
    clip = ImageClip(video_path).set_duration(8)  # keep video length consistent
    clip.write_videofile(output_path, fps=24)
    return output_path

# 📤 Upload to YouTube
def upload_to_youtube(file_path, title, description, tags):
    creds_data = json.loads(TOKEN_JSON)
    creds = Credentials.from_authorized_user_info(creds_data, ["https://www.googleapis.com/auth/youtube.upload"])

    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(file_path, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"✅ Uploaded! Video ID: {response['id']}")

# 🚀 Main pipeline
if __name__ == "__main__":
    try:
        metadata = generate_concept_and_metadata()
        print("✅ Metadata generated:", metadata)

        video_path = os.path.join(VIDEOS_DIR, "final_video.mp4")
        success = generate_video(metadata["video_prompt"], video_path)

        if not success:
            print("⚠️ Falling back to image → video pipeline")
            img_clip = ImageClip("fallback.jpg").set_duration(8).resize((1080, 1920))
            img_clip.write_videofile(video_path, fps=24)

        # Upload
        upload_to_youtube(
            video_path,
            metadata["title"],
            metadata["description"] + "\n" + " ".join(metadata["hashtags"]),
            metadata["tags"]
        )

        print("🎉 Pipeline complete!")

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
                      
