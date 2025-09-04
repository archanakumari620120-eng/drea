import os
import schedule
import time
import random
import requests
from moviepy.editor import *
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ====== DEBUG START ======
print("✅ Script started...")
# ====== DEBUG END ======

# Load credentials
def get_youtube_service():
    print("🔑 Loading YouTube credentials...")
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    else:
        raise Exception("❌ token.json not found. Run OAuth flow locally once.")
    
    print("✅ YouTube credentials loaded.")
    return build("youtube", "v3", credentials=creds)


# Generate a sample video
def generate_video():
    print("🎬 Generating video...")
    txt = TextClip("Hello YouTube Shorts!", fontsize=70, color="white", size=(1080,1920))
    txt = txt.set_duration(10)
    txt = txt.set_position("center")
    
    output = "output.mp4"
    txt.write_videofile(output, fps=24)
    print("✅ Video generated:", output)
    return output


# Upload to YouTube
def upload_video(file_path):
    print("📤 Uploading video to YouTube...")

    youtube = get_youtube_service()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"Test Shorts {random.randint(1000,9999)}",
                "description": "Uploaded via GitHub Actions",
                "tags": ["shorts", "automation", "test"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(file_path)
    )

    response = request.execute()
    print("✅ Upload complete. Video ID:", response.get("id"))


# Main job
def job():
    print("🚀 Job started...")
    try:
        video_file = generate_video()
        upload_video(video_file)
        print("🎉 Job finished successfully.")
    except Exception as e:
        print("❌ ERROR in job:", str(e))


if __name__ == "__main__":
    print("🔄 Running main script once (for debug)...")
    job()
