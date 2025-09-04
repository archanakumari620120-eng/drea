import os
from moviepy.editor import ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Load config from environment
CFG = {
    "client_id": os.getenv("YT_CLIENT_ID"),
    "client_secret": os.getenv("YT_CLIENT_SECRET"),
    "refresh_token": os.getenv("YT_REFRESH_TOKEN"),
    "api_key": os.getenv("YT_API_KEY", ""),
    "visibility": "public"
}

# Step 1: Create dummy short video
def create_dummy_video(path="short.mp4"):
    clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=5)
    clip.write_videofile(path, fps=24)
    return path

# Step 2: Upload to YouTube
def upload_youtube(video_path, title="Test Video", desc="Uploaded via GitHub Actions"):
    creds = Credentials(
        None,
        refresh_token=CFG["refresh_token"],
        client_id=CFG["client_id"],
        client_secret=CFG["client_secret"],
        token_uri="https://oauth2.googleapis.com/token"
    )

    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": desc,
                "tags": ["AI", "shorts", "test"]
            },
            "status": {"privacyStatus": CFG["visibility"]}
        },
        media_body=MediaFileUpload(video_path)
    )
    response = request.execute()
    print("✅ Upload successful:", response)

def main():
    video_path = create_dummy_video()
    upload_youtube(video_path)

if _name_ == "_main_":
    main()
