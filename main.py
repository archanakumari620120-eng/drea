import os
import time
import random
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------------
# CONFIG LOAD
# ---------------------------
def load_config():
    config = {}
    # GitHub secrets se read
    client_id = os.getenv("YT_CLIENT_ID")
    client_secret = os.getenv("YT_CLIENT_SECRET")
    refresh_token = os.getenv("YT_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        config["client_id"] = client_id
        config["client_secret"] = client_secret
        config["refresh_token"] = refresh_token
    else:
        # fallback: config.json se
        import json
        with open("config.json", "r") as f:
            config = json.load(f)
    return config

# ---------------------------
# GET YOUTUBE SERVICE
# ---------------------------
def get_youtube_service(cfg):
    creds = Credentials(
        None,
        refresh_token=cfg["refresh_token"],
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build("youtube", "v3", credentials=creds)

# ---------------------------
# SIMPLE VIDEO MAKER (Placeholder)
# ---------------------------
def create_dummy_video():
    # Dummy mp4 banayega ek simple black screen ke saath
    import cv2
    import numpy as np

    height, width = 1920, 1080
    duration = 5  # seconds
    fps = 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter("output.mp4", fourcc, fps, (width, height))

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for _ in range(duration * fps):
        out.write(frame)
    out.release()

    return "output.mp4"

# ---------------------------
# UPLOAD VIDEO
# ---------------------------
def upload_video(youtube, file_path, title, description, tags, privacy="public"):
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )
    response = request.execute()
    print("✅ Uploaded:", response["id"])

# ---------------------------
# MAIN
# ---------------------------
if _name_ == "_main_":
    cfg = load_config()
    youtube = get_youtube_service(cfg)

    # Dummy video (baad me AI video generation replace kar sakte ho)
    video_file = create_dummy_video()

    title = f"AI Shorts - {random.randint(1000,9999)}"
    description = "Generated automatically with AI."
    tags = ["AI", "shorts", "trending"]

    upload_video(youtube, video_file, title, description, tags)
