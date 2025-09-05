import os
import random
import time
import json
import schedule
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ✅ Safe resampling (fix for Pillow v10+)
if hasattr(Image, "Resampling"):
    RESAMPLE = Image.Resampling.LANCZOS
else:
    RESAMPLE = Image.ANTIALIAS

# Load config
with open("config.json", "r") as f:
    CONFIG = json.load(f)

# Paths
IMAGES_DIR = "images"
MUSIC_DIR = "music"
OUTPUTS_DIR = "outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# YouTube Auth
creds = Credentials.from_authorized_user_file("token.json")

def generate_video():
    try:
        # Pick random image
        images = [os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            print("❌ No images found in 'images/' folder.")
            return None
        img_path = random.choice(images)

        img = Image.open(img_path)
        img = img.resize((1080, 1920), RESAMPLE)
        fixed_img_path = os
        
