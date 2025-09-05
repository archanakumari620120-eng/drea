import os, random, json, time, requests, logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load config
with open("config.json") as f:
    CONFIG = json.load(f)

# YouTube auth
creds = Credentials(
    None,
    refresh_token=CONFIG["refresh_token"],
    client_id=CONFIG["client_id"],
    client_secret=CONFIG["client_secret"],
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

# --- AI Prompt Generation ---
def generate_prompt():
    try:
        headers = {"Authorization": f"Bearer {CONFIG['gemini_api_key']}"}
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + CONFIG['gemini_api_key'],
                          json={"contents":[{"parts":[{"text":"Give me a short creative idea for a video"}]}]})
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        logging.warning("Gemini failed, fallback HuggingFace")
        headers = {"Authorization": f"Bearer {CONFIG['hf_token']}"}
        r = requests.post("https://api-inference.huggingface.co/models/gpt2",
                          headers=headers, json={"inputs":"Give me a short creative idea"})
        return r.json()[0]["generated_text"]

# --- Image Selection ---
def get_image():
    img_dir = "images"
    files = os.listdir(img_dir)
    if files:
        return os.path.join(img_dir, random.choice(files))
    # fallback pexels
    headers = {"Authorization": CONFIG["pexels_api_key"]}
    r = requests.get("https://api.pexels.com/v1/search", headers=headers, params={"query": random.choice(CONFIG["pexels_query"]), "per_page":1})
    data = r.json()
    if data["photos"]:
        url = data["photos"][0]["src"]["large"]
        fname = "temp.jpg"
        with open(fname, "wb") as f: f.write(requests.get(url).content)
        return fname
    return None

# --- Music Selection ---
def get_music():
    music_dir = "music"
    files = os.listdir(music_dir)
    if files:
        return os.path.join(music_dir, random.choice(files))
    return None

# --- Video Generation (simple ffmpeg style with image + audio) ---
def create_video(image_path, music_path, out_path="output.mp4"):
    os.system(f"ffmpeg -loop 1 -i {image_path} -i {music_path} -c:v libx264 -t {CONFIG['video_length_sec']} -pix_fmt yuv420p -vf scale={CONFIG['target_resolution'][0]}:{CONFIG['target_resolution'][1]} {out_path} -y")
    return out_path

# --- Upload to YouTube ---
def upload_video(file, title, desc, tags, privacy):
    logging.info("Uploading video...")
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": desc,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": privacy}
        },
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True)
    )
    response = request.execute()
    logging.info(f"✅ Uploaded: https://youtu.be/{response['id']}")

# --- Main ---
if __name__ == "__main__":
    logging.info("🚀 Script started")
    prompt = generate_prompt()
    image = get_image()
    music = get_music()
    video = create_video(image, music)
    title = CONFIG["video_title_template"].format(prompt=prompt)
    desc = CONFIG["video_description_template"].format(prompt=prompt)
    upload_video(video, title, desc, CONFIG["video_tags"], CONFIG["visibility"])
    logging.info("🎬 Done")
