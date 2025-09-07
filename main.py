# main.py - Final uploader (single run). Scheduler handled by GitHub Actions.
import os, json, time, random, traceback
from pathlib import Path
import requests
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

OUTPUTS = Path("outputs")
OUTPUTS.mkdir(exist_ok=True)
IMAGES_DIR = Path("images")
MUSIC_DIR = Path("music")
TOKEN_PATH = "token.json"

# Load env or config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_KEY")
if os.path.exists("config.json"):
    try:
        cfg = json.load(open("config.json"))
        GEMINI_API_KEY = GEMINI_API_KEY or cfg.get("GEMINI_API_KEY") or cfg.get("gemini_api_key")
        HF_TOKEN = HF_TOKEN or cfg.get("HF_API_KEY") or cfg.get("hf_token")
    except Exception:
        pass

# Pillow resampling safe
try:
    from PIL import Image as PILImage
    RESAMPLE = PILImage.Resampling.LANCZOS if hasattr(PILImage, "Resampling") else PILImage.ANTIALIAS
except Exception:
    RESAMPLE = None

if not os.path.exists(TOKEN_PATH):
    raise FileNotFoundError("token.json not found. Put it via GitHub secret TOKEN_JSON or place locally.")
creds = Credentials.from_authorized_user_file(TOKEN_PATH)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def safe_write(path, b):
    with open(path, "wb") as f:
        f.write(b)

FALLBACK_PROMPTS = [
    "Never give up!",
    "Quick life-hack to stay focused",
    "Amazing tiny fact about space",
    "One motivational tip in 15 seconds"
]

def prompt_from_gemini():
    if not GEMINI_API_KEY:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5:generateContent"
        payload = {"contents":[{"parts":[{"text":"Give a short catchy idea for a YouTube Short (<=12 words)."}]}]}
        r = requests.post(url, params={"key":GEMINI_API_KEY}, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        cand = data.get("candidates") or []
        if cand:
            text = cand[0].get("content", {}).get("parts", [])[0].get("text")
            if text:
                return text.strip()
    except Exception as e:
        log("Gemini prompt error: " + str(e))
    return None

def prompt_from_hf():
    if not HF_TOKEN:
        return None
    try:
        url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs":"Give a short catchy idea for a YouTube Short (<=12 words)."}
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.ok:
            out = r.json()
            if isinstance(out, list) and out and "generated_text" in out[0]:
                return out[0]["generated_text"].strip()
            if isinstance(out, dict) and "generated_text" in out:
                return out["generated_text"].strip()
    except Exception as e:
        log("HF prompt error: " + str(e))
    return None

def get_prompt():
    p = prompt_from_gemini()
    if p:
        return p
    p = prompt_from_hf()
    if p:
        return p
    return random.choice(FALLBACK_PROMPTS)

def image_from_gemini(prompt):
    if not GEMINI_API_KEY:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-image:generateImage"
        payload = {"prompt": prompt}
        r = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, timeout=60)
        if r.ok:
            data = r.json()
            img_url = data.get("image") or data.get("url")
            if img_url:
                b = requests.get(img_url, timeout=30).content
                out = OUTPUTS / "gemini_img.jpg"
                safe_write(out, b)
                return str(out)
            b64 = data.get("b64") or data.get("image_b64")
            if b64:
                import base64
                safe_write(OUTPUTS / "gemini_img.jpg", base64.b64decode(b64))
                return str(OUTPUTS / "gemini_img.jpg")
    except Exception as e:
        log("Gemini image error: " + str(e))
    return None

def image_from_hf(prompt):
    if not HF_TOKEN:
        return None
    try:
        url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
        if r.status_code == 200:
            out = OUTPUTS / "hf_img.jpg"
            safe_write(out, r.content)
            return str(out)
        else:
            log(f"HF image failed status {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log("HF image exception: " + str(e))
    return None

def pick_local_image():
    if not IMAGES_DIR.exists():
        return None
    imgs = [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp')]
    return str(random.choice(imgs)) if imgs else None

def generate_image(prompt):
    img = image_from_gemini(prompt)
    if img:
        return img
    img = image_from_hf(prompt)
    if img:
        return img
    return pick_local_image()

def pick_music():
    if not MUSIC_DIR.exists():
        return None
    mus = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in ('.mp3','.wav','.m4a')]
    return str(random.choice(mus)) if mus else None

def build_video(image_path, music_path, duration=15):
    try:
        img = Image.open(image_path).convert('RGB')
        if RESAMPLE:
            img = img.resize((1080,1920), RESAMPLE)
        else:
            img = img.resize((1080,1920))
        frame = OUTPUTS / 'frame.jpg'
        img.save(frame, quality=90)

        clip = ImageClip(str(frame)).set_duration(duration)
        audio = AudioFileClip(music_path).subclip(0, duration)
        clip = clip.set_audio(audio)

        out = OUTPUTS / f'short_{int(time.time())}.mp4'
        clip.write_videofile(str(out), fps=30, codec='libx264', audio_codec='aac')
        return str(out)
    except Exception as e:
        log('Build video error: ' + str(e))
        log(traceback.format_exc())
        return None

def gen_metadata(prompt):
    title = (prompt[:55] if prompt else 'AI Short').strip()
    uniq = str(int(time.time()))[-5:]
    return {'title': f"{title} #{uniq}", 'description': f"Auto-generated AI Short. Prompt: {prompt}", 'tags': ['AI','shorts']}

def upload_to_youtube(video_path, metadata):
    try:
        yt = build('youtube','v3', credentials=creds)
        body = {
            'snippet': {
                'title': metadata.get('title'),
                'description': metadata.get('description'),
                'tags': metadata.get('tags'),
                'categoryId': '22'
            },
            'status': {'privacyStatus':'public'}
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
        log('Uploading...')
        resp = req.execute()
        log('Uploaded id: ' + str(resp.get('id')))
        return resp.get('id')
    except Exception as e:
        log('Upload error: ' + str(e))
        log(traceback.format_exc())
        return None

def job():
    log('=== JOB START ===')
    prompt = get_prompt()
    log('Prompt: ' + str(prompt))
    img = generate_image(prompt)
    if not img:
        log('No image, abort.')
        return
    music = pick_music()
    if not music:
        log('No music, abort.')
        return
    video = build_video(img, music, duration=int(15))
    if not video:
        log('Video build failed.')
        return
    meta = gen_metadata(prompt)
    upload_to_youtube(video, meta)
    log('=== JOB END ===')

if __name__ == '__main__':
    job()
