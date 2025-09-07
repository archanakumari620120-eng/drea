# main.py — Final: Gemini prompt → Gemini video → Gemini image → HF image → manual fallback
import os
import time
import json
import random
import traceback
import base64
from pathlib import Path

import requests
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Try import google genai (official library). If not present, we'll still attempt HTTP calls where possible.
try:
    import google.genai as genai
    from google.genai import types
    HAVE_GEMINI_LIB = True
except Exception:
    HAVE_GEMINI_LIB = False

# -------------------- Config & paths --------------------
with open("config.json", "r") as f:
    CONFIG = json.load(f)

# ensure outputs
OUTPUTS = Path("outputs")
OUTPUTS.mkdir(exist_ok=True)
IMAGES_DIR = Path("images")
MUSIC_DIR = Path("music")
TOKEN_FILE = "token.json"

# Pillow safe resampling (ANTIALIAS fix)
if hasattr(Image, "Resampling"):
    RESAMPLE = Image.Resampling.LANCZOS
else:
    RESAMPLE = Image.ANTIALIAS

# YouTube creds (must exist)
creds = Credentials.from_authorized_user_file(TOKEN_FILE)

# -------------------- Utilities --------------------
def log(s):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {s}", flush=True)

def safe_write_bytes(path: Path, b: bytes):
    with open(path, "wb") as f:
        f.write(b)

# -------------------- Prompt (Gemini primary) --------------------
FALLBACK_PROMPTS = [
    "A cinematic slow-motion ocean waves at sunset, soft piano (short)",
    "Quick life-hack for focus in under 8 seconds",
    "Amazing space fact with dramatic reveal",
    "Tiny productivity tip you can use today",
    "Funny one-line joke with quick punchline"
]

def gen_prompt_gemini():
    try:
        if HAVE_GEMINI_LIB:
            genai.configure(api_key=CONFIG.get("GEMINI_API_KEY"))
            client = genai.Client()
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Give a short (<=12 words) catchy idea for a YouTube Short (no hashtags)."
            )
            text = getattr(resp, "text", None) or (resp.candidates[0].content.parts[0].text if getattr(resp, "candidates", None) else None)
            if text:
                return text.strip()
        else:
            # HTTP call to Generative Language API (if key present)
            key = CONFIG.get("GEMINI_API_KEY")
            if key:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5:generateContent"
                payload = {"contents":[{"parts":[{"text":"Give a short catchy idea for a YouTube Short (<=12 words)."}]}]}
                r = requests.post(url, params={"key": key}, json=payload, timeout=20)
                r.raise_for_status()
                data = r.json()
                cand = data.get("candidates") or []
                if cand:
                    txt = cand[0].get("content", {}).get("parts", [])[0].get("text")
                    if txt:
                        return txt.strip()
    except Exception as e:
        log("Gemini prompt failed: " + str(e))
        log(traceback.format_exc())
    return None

def get_prompt():
    p = gen_prompt_gemini()
    if p:
        return p
    return random.choice(FALLBACK_PROMPTS)

# -------------------- Gemini Video (experimental) --------------------
def gen_gemini_video(prompt: str):
    """Try to generate a video via Gemini Veo model (if supported by account & library).
       Returns local video path or None."""
    try:
        if not HAVE_GEMINI_LIB:
            log("Gemini library not installed — skipping Gemini video step.")
            return None
        genai.configure(api_key=CONFIG.get("GEMINI_API_KEY"))
        client = genai.Client()

        log("Requesting Gemini video generation (veo)...")
        op = client.models.generate_videos(
            model="veo-3.0-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=int(CONFIG.get("video_generation", {}).get("duration_seconds", 8)),
                negative_prompt="low quality, blurry, text"
            )
        )
        # Poll operation
        # Note: API shape may vary; handle generically
        wait_seconds = 5
        for _ in range(120):  # up to ~10 minutes polling (adjust as needed)
            if getattr(op, "done", False):
                break
            log("Waiting for Gemini video... sleeping {}s".format(wait_seconds))
            time.sleep(wait_seconds)
            try:
                op = client.operations.get(op)
            except Exception:
                time.sleep(wait_seconds)
        if not getattr(op, "done", False):
            log("Gemini video operation not completed in time.")
            return None
        # Extract generated videos
        result = getattr(op, "result", None)
        if not result:
            log("No result from Gemini video op.")
            return None
        gen_videos = getattr(result, "generated_videos", None)
        if gen_videos and len(gen_videos) > 0:
            video_bytes = getattr(gen_videos[0].video, "video_bytes", None)
            if video_bytes:
                out = OUTPUTS / "gemini_video.mp4"
                safe_write_bytes(out, video_bytes)
                log(f"Gemini video saved: {out}")
                return str(out)
        # Some responses may embed base64 or urls — try to parse common fields
        try:
            # fallback: if op.result contains urls
            urls = []
            if isinstance(result, dict):
                # result may be dict-like
                vids = result.get("generated_videos") or []
                for v in vids:
                    b = v.get("video", {}).get("video_bytes")
                    if b:
                        safe_write_bytes(OUTPUTS / "gemini_video.mp4", b)
                        return str(OUTPUTS / "gemini_video.mp4")
        except Exception:
            pass
    except Exception as e:
        log("Gemini video generation failed: " + str(e))
        log(traceback.format_exc())
    return None

# -------------------- Gemini Image (text->image) --------------------
def gen_gemini_image(prompt: str):
    """Try Gemini image generation (if supported). If returns bytes or URL, save and return path."""
    try:
        if HAVE_GEMINI_LIB:
            # gemini image generation via models.generate_content or dedicated image method if available
            genai.configure(api_key=CONFIG.get("GEMINI_API_KEY"))
            client = genai.Client()
            # This example uses a generic generate_content with request hinting for image output;
            # actual behavior depends on account & model support.
            resp = client.models.generate_content(
                model="gemini-2.5-image",  # placeholder; your account may have different model name
                contents=f"Generate a high-quality vertical image for this short: {prompt}"
            )
            # attempt to extract inline image data if present
            txt = getattr(resp, "text", None)
            # If response contains base64 inline data, try to decode (this is best-effort)
            # If not, skip and return None.
            return None
        else:
            log("Gemini lib missing for image; skipping Gemini image.")
            return None
    except Exception as e:
        log("Gemini image failed: " + str(e))
        log(traceback.format_exc())
        return None

# -------------------- HuggingFace Image --------------------
def gen_hf_image(prompt: str):
    try:
        hf_token = CONFIG.get("HF_API_KEY") or CONFIG.get("hf_token") or CONFIG.get("HUGGINGFACE_API_KEY")
        if not hf_token:
            log("No HF token provided.")
            return None
        url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {"inputs": prompt}
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            out_path = OUTPUTS / "hf_image.jpg"
            safe_write_bytes(out_path, r.content)
            log(f"HuggingFace image saved: {out_path}")
            return str(out_path)
        else:
            log(f"HF image call failed status {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log("HuggingFace image error: " + str(e))
        log(traceback.format_exc())
    return None

# -------------------- Manual fallback image --------------------
def pick_manual_image():
    if not IMAGES_DIR.exists():
        return None
    imgs = [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not imgs:
        return None
    return str(random.choice(imgs))

# -------------------- Build video from image + music --------------------
def build_video_from_image(image_path: str, music_path: str, duration: int = 15):
    try:
        img = Image.open(image_path).convert("RGB")
        img = img.resize((1080, 1920), RESAMPLE)
        fixed = OUTPUTS / "frame.jpg"
        img.save(fixed, quality=95)

        clip = ImageClip(str(fixed)).set_duration(duration)
        audio = AudioFileClip(music_path).subclip(0, duration)
        clip = clip.set_audio(audio)

        outp = OUTPUTS / f"short_{int(time.time())}.mp4"
        clip.write_videofile(str(outp), fps=30, codec="libx264", audio_codec="aac")
        log(f"Video created: {outp}")
        return str(outp)
    except Exception as e:
        log("Error building video: " + str(e))
        log(traceback.format_exc())
        return None

# -------------------- Pick music --------------------
def pick_music():
    if not MUSIC_DIR.exists():
        return None
    mus = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    if not mus:
        return None
    return str(random.choice(mus))

# -------------------- Metadata via Gemini (optional) --------------------
def gen_metadata(prompt: str):
    try:
        if HAVE_GEMINI_LIB:
            genai.configure(api_key=CONFIG.get("GEMINI_API_KEY"))
            client = genai.Client()
            md_request = f"""Based on this prompt: {prompt}
Generate JSON: {{ "title":"<short title under 60 chars>", "description":"<short description>", "tags":["tag1","tag2"] }}"""
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=md_request)
            text = getattr(resp, "text", None) or (resp.candidates[0].content.parts[0].text if getattr(resp, "candidates", None) else None)
            if text:
                try:
                    return json.loads(text)
                except Exception:
                    pass
        # HTTP fallback attempt (rare)
    except Exception as e:
        log("Gemini metadata failed: " + str(e))
    # fallback metadata
    uniq = str(int(time.time()))[-5:]
    return {
        "title": f"{prompt[:55]} #{uniq}",
        "description": f"{prompt}\nAuto-generated with AI.",
        "tags": CONFIG.get("youtube", {}).get("default_tags", ["AI", "Shorts"])
    }

# -------------------- Upload to YouTube --------------------
def upload_to_youtube(video_path: str, metadata: dict):
    try:
        yt = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": metadata.get("title", "AI Short"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": str(CONFIG.get("youtube", {}).get("category_id", "22"))
            },
            "status": {"privacyStatus": CONFIG.get("youtube", {}).get("privacy_status", "public")}
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        log("Starting upload...")
        resp = req.execute()
        vid = resp.get("id")
        log(f"Uploaded video id: {vid}")
        return vid
    except Exception as e:
        log("YouTube upload failed: " + str(e))
        log(traceback.format_exc())
        return None

# -------------------- Main job --------------------
def job():
    log("=== JOB START ===")
    prompt = get_prompt()
    log(f"Prompt: {prompt}")

    # Try Gemini video
    vid_path = gen_gemini_video(prompt)
    if vid_path:
        log("Using Gemini-generated video.")
        metadata = gen_metadata(prompt)
        upload_to_youtube(vid_path, metadata)
        return

    # Try Gemini image
    img_path = gen_gemini_image(prompt)
    if not img_path:
        # Try HuggingFace image
        img_path = gen_hf_image(prompt)
    if not img_path:
        # Final manual fallback
        img_path = pick_manual_image()
    if not img_path:
        log("No image available, aborting.")
        return

    # Pick music
    music = pick_music()
    if not music:
        log("No music available, aborting.")
        return

    # Build video from image+music
    video = build_video_from_image(img_path, music, duration=int(CONFIG.get("video_generation", {}).get("duration_seconds", 15)))
    if not video:
        log("Failed to build video.")
        return

    # metadata & upload
    metadata = gen_metadata(prompt)
    upload_to_youtube(video, metadata)

    log("=== JOB END ===")

# -------------------- Execute single run --------------------
if __name__ == "__main__":
    job()
            
