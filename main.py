import os, random, time, json, requests, schedule
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip, VideoFileClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle

# ---------------- CONFIG ---------------- #
with open("config.json", "r") as f:
    CONFIG = json.load(f)

GEMINI_KEY = CONFIG["gemini_api_key"]
HF_TOKEN = CONFIG["huggingface_token"]
PEXELS_KEY = CONFIG["pexels_api_key"]
CLIENT_SECRET_FILE = CONFIG["youtube"]["client_secrets_file"]
REDIRECT_PORT = CONFIG["youtube"]["redirect_port"]

# ---------------- YOUTUBE AUTH ---------------- #
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES, redirect_uri=f"http://localhost:{REDIRECT_PORT}/")
            creds = flow.run_local_server(port=REDIRECT_PORT)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

youtube = get_youtube_service()

# ---------------- AI HELPERS ---------------- #
def generate_prompt():
    # Gemini से prompt/title/desc/tags generate
    prompt = f"Generate a motivational short about {random.choice(['success','focus','consistency','patience'])}"
    return {
        "title": f"{prompt} #shorts",
        "description": f"{prompt} - Daily Motivation",
        "tags": ["motivation","shorts","success"],
        "prompt": prompt
    }

def get_gemini_video(prompt):
    # Dummy fallback (real Gemini video API integrate करना होगा)
    return None  

def get_hf_video(prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # HuggingFace से video API call (simplified placeholder)
    return None  

def get_pexels_video():
    headers = {"Authorization": PEXELS_KEY}
    r = requests.get("https://api.pexels.com/videos/popular?per_page=1", headers=headers)
    if r.status_code == 200 and r.json()["videos"]:
        link = r.json()["videos"][0]["video_files"][0]["link"]
        os.system(f"wget -O temp_video.mp4 \"{link}\"")
        return "temp_video.mp4"
    return None

def get_fallback_image_video(prompt):
    # अगर कुछ नहीं मिला तो image → video बनाना
    img_path = "images"
    if not os.path.exists(img_path) or not os.listdir(img_path):
        return None
    images = [os.path.join(img_path, i) for i in os.listdir(img_path)]
    clip = ImageSequenceClip(images, fps=1).set_duration(len(images)*2)
    clip.write_videofile("fallback.mp4", fps=24)
    return "fallback.mp4"

# ---------------- MUSIC ---------------- #
def get_music():
    music_dir = "music"
    if os.path.exists(music_dir) and os.listdir(music_dir):
        return os.path.join(music_dir, random.choice(os.listdir(music_dir)))
    return None  # fallback: YouTube no-copyright download यहाँ add कर सकते हैं

# ---------------- VIDEO PIPELINE ---------------- #
def create_video():
    meta = generate_prompt()
    video_file = None
    
    video_file = get_gemini_video(meta["prompt"])
    if not video_file:
        video_file = get_hf_video(meta["prompt"])
    if not video_file:
        video_file = get_pexels_video()
    if not video_file:
        video_file = get_fallback_image_video(meta["prompt"])
    
    if not video_file:
        print("❌ Video generation failed")
        return None, None

    music = get_music()
    if music:
        final = "final.mp4"
        clip = VideoFileClip(video_file)
        audio = AudioFileClip(music)
        clip = clip.set_audio(audio)
        clip.write_videofile(final, fps=24)
        return final, meta
    return video_file, meta

# ---------------- UPLOAD ---------------- #
def upload_video(file, meta, privacy="private"):
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": privacy
        }
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=file
    )
    response = request.execute()
    print(f"✅ Uploaded: {meta['title']}")
    return response

# ---------------- SCHEDULER ---------------- #
def run_batch():
    for i in range(6):  # 6 videos in one run
        file, meta = create_video()
        if file:
            upload_video(file, meta, "private")
        time.sleep(5)

def make_public(video_id):
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": "public"}}
    ).execute()
    print(f"🌍 Made public: {video_id}")

# Start batch once
run_batch()
# हर 4 घंटे बाद scheduler से public करना (यहाँ IDs list में डालनी होंगी upload के बाद)