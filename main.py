import os
import json
import traceback
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ---------------- Load Config ----------------
print("🔑 Loading config.json ...")
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except Exception as e:
    print("❌ Error loading config.json:", e)
    traceback.print_exc()
    exit(1)

# ---------------- Video Generation ----------------
def generate_video():
    try:
        print("🎬 Starting video generation...")
        images = [os.path.join("images", img) for img in os.listdir("images") if img.endswith((".jpg", ".png"))]
        if not images:
            print("❌ No images found in /images")
            return None

        clips = []
        for img in images:
            print(f"🖼️ Adding image: {img}")
            clip = ImageClip(img).set_duration(3).resize(height=1920, width=1080)
            clips.append(clip)

        final = concatenate_videoclips(clips, method="compose")

        # Add music if available
        music_files = [os.path.join("music", m) for m in os.listdir("music") if m.endswith(".mp3")]
        if music_files:
            print(f"🎵 Adding background music: {music_files[0]}")
            audio = AudioFileClip(music_files[0])
            final = final.set_audio(audio)

        output_path = "output.mp4"
        final.write_videofile(output_path, fps=24)
        print(f"✅ Video generated: {output_path}")
        return output_path
    except Exception as e:
        print("❌ Error in video generation:", e)
        traceback.print_exc()
        return None

# ---------------- YouTube Upload ----------------
def upload_to_youtube(video_path):
    try:
        print("📤 Starting YouTube upload...")
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)

        request_body = {
            "snippet": {
                "title": "AI Generated Video",
                "description": "This video was auto-uploaded using AI 🎬",
                "tags": ["AI", "automation", "YouTube Shorts"]
            },
            "status": {"privacyStatus": "private"}
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")
        request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
        response = request.execute()

        print("✅ Upload complete, video ID:", response["id"])
    except Exception as e:
        print("❌ Error in YouTube upload:", e)
        traceback.print_exc()

# ---------------- Main ----------------
if __name__ == "__main__":
    video_file = generate_video()
    if video_file:
        upload_to_youtube(video_file)
    else:
        print("⚠️ Skipping upload because video generation failed.")
        
