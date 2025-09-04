import os
import time
import random
import logging
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ===============================
# CONFIG (direct inside main.py)
# ===============================
CONFIG = {
    "client_id": "1//0gi7F7NZGIqJiCgYIARAAGBASNwF-L9IrEFAd2hdzmg3CREdZRPAQY1UdBbmKxv1uv2vqszqrxkBNenGrmz63A-xEyOtMIPTlITg",
    "client_secret": "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",
    "refresh_token": "1//0gi7F7NZGIqJiCgYIARAAGBASNwF-L9IrEFAd2hdzmg3CREdZRPAQY1UdBbmKxv1uv2vqszqrxkBNenGrmz63A-xEyOtMIPTlITg",

    "video_length_sec": 15,
    "target_resolution": (1080, 1920),

    "pexels_query": [
        "nature", "space", "city", "abstract",
        "technology", "timelapse", "clouds",
        "neon", "mountains"
    ],

    "visibility": "public",
    "upload_interval_hours": 5,

    "video_title_template": "AI Shorts - {prompt}",
    "video_description_template": "Generated automatically with AI.\nPrompt: {prompt}",
    "video_tags": ["AI", "shorts", "trending"]
}

# ===============================
# LOGGING SETUP
# ===============================
logging.basicConfig(
    filename="run.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ===============================
# YOUTUBE AUTH
# ===============================
def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=CONFIG["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CONFIG["client_id"],
        client_secret=CONFIG["client_secret"]
    )
    return build("youtube", "v3", credentials=creds)

# ===============================
# VIDEO GENERATOR
# ===============================
def generate_video(prompt):
    images = [f for f in os.listdir("images") if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    musics = [f for f in os.listdir("music") if f.lower().endswith((".mp3", ".wav"))]

    if not images or not musics:
        raise FileNotFoundError("❌ Image or music file missing!")

    image_file = os.path.join("images", random.choice(images))
    music_file = os.path.join("music", random.choice(musics))

    logging.info(f"🎨 Using Image={image_file} | 🎵 Music={music_file}")

    clip = ImageClip(image_file).set_duration(CONFIG["video_length_sec"]).resize(newsize=CONFIG["target_resolution"])
    audio = AudioFileClip(music_file).subclip(0, CONFIG["video_length_sec"])
    final = clip.set_audio(audio)

    output_file = "output.mp4"
    final.write_videofile(output_file, fps=30, codec="libx264", audio_codec="aac", verbose=False, logger=None)

    return output_file, image_file, music_file

# ===============================
# YOUTUBE UPLOAD
# ===============================
def upload_video(file_path, title, description, tags, visibility="public"):
    youtube = get_youtube_service()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": visibility,
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=file_path
    )
    try:
        response = request.execute()
        video_id = response["id"]
        logging.info(f"✅ Uploaded VideoID={video_id} | Title={title}")
        print(f"Uploaded Video: https://youtu.be/{video_id}")
    except HttpError as e:
        logging.error(f"❌ Upload failed: {str(e)}")
        print(f"Upload failed: {str(e)}")

# ===============================
# MAIN LOOP
# ===============================
if __name__ == "__main__":
    while True:
        prompt = random.choice(CONFIG["pexels_query"])
        try:
            # Generate
            video_file, img, mus = generate_video(prompt)
            title = CONFIG["video_title_template"].format(prompt=prompt)
            description = CONFIG["video_description_template"].format(prompt=prompt)

            # Upload
            upload_video(video_file, title, description, CONFIG["video_tags"], CONFIG["visibility"])

            # Clean
            if os.path.exists(video_file):
                os.remove(video_file)

        except Exception as e:
            logging.error(f"❌ Error: {str(e)}")
            print(f"Error: {str(e)}")

        logging.info(f"⏰ Sleeping for {CONFIG['upload_interval_hours']} hours...")
        time.sleep(CONFIG["upload_interval_hours"] * 3600)
