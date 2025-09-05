import os
import random
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import json

def generate_video():
    # Ensure images/music exist
    images = os.listdir("images")
    musics = os.listdir("music")

    if not images or not musics:
        raise Exception("❌ No images or music found!")

    image = os.path.join("images", random.choice(images))
    music = os.path.join("music", random.choice(musics))

    clip = ImageClip(image).set_duration(30).resize((1080, 1920))
    audio = AudioFileClip(music).subclip(0, 30)
    clip = clip.set_audio(audio)

    output = "output.mp4"
    clip.write_videofile(output, fps=24, codec="libx264", audio_codec="aac")
    return output

def upload_video(file):
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Auto Short Upload 🚀",
                "description": "Uploaded automatically",
                "tags": ["shorts", "auto", "upload"]
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(file)
    )
    response = request.execute()
    print("✅ Uploaded successfully! Video ID:", response["id"])

if __name__ == "__main__":
    video = generate_video()
    upload_video(video)
