import os
import json
import time
import requests
from moviepy.editor import VideoFileClip, concatenate_videoclips

# 🔹 Config load + Env override
with open("config.json", "r") as f:
    CFG = json.load(f)

CFG["client_id"]      = os.getenv("YT_CLIENT_ID",     CFG.get("client_id"))
CFG["client_secret"]  = os.getenv("YT_CLIENT_SECRET", CFG.get("client_secret"))
CFG["refresh_token"]  = os.getenv("YT_REFRESH_TOKEN", CFG.get("refresh_token"))
CFG["gemini_api_key"] = os.getenv("GEMINI_API_KEY",   CFG.get("gemini_api_key"))
CFG["hf_token"]       = os.getenv("HF_TOKEN",         CFG.get("hf_token"))
CFG["pexels_api_key"] = os.getenv("PEXELS_API_KEY",   CFG.get("pexels_api_key"))

# ✅ Dummy video maker (replace with your own logic)
def make_video(output_path="short.mp4"):
    clip1 = VideoFileClip("assets/clip1.mp4")
    clip2 = VideoFileClip("assets/clip2.mp4")
    final = concatenate_videoclips([clip1, clip2])
    final.write_videofile(output_path, codec="libx264", fps=30)
    print(f"Video created: {output_path}")
    return output_path

# ✅ Dummy YouTube uploader (replace with google-api-python-client logic)
def upload_youtube(filepath, title, desc, visibility="public"):
    if not CFG["client_id"] or not CFG["client_secret"] or not CFG["refresh_token"]:
        raise RuntimeError("❌ Missing YouTube API secrets. Check repo → Settings → Secrets.")
    print(f"Uploading {filepath} to YouTube...")
    time.sleep(3)  # Simulate API call
    print(f"✅ Uploaded {filepath} as '{title}'")

def main():
    video = make_video("outputs/short.mp4")
    upload_youtube(video, title="AI Generated Shorts", desc="Automated upload test")

if _name_ == "_main_":
    main()
