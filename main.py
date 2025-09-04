import os, json, math, random, requests, tempfile
from pathlib import Path
from typing import Optional, Tuple

from moviepy.editor import (
    VideoFileClip, ImageClip, ColorClip, AudioFileClip, concatenate_videoclips
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials


# ---------- Load config + Env overrides ----------
def load_config() -> dict:
    with open("config.json", "r") as f:
        cfg = json.load(f)

    # Env vars override (GitHub Secrets)
    def ov(key_env, key_cfg):
        v = os.getenv(key_env)
        if v and v.strip():
            cfg[key_cfg] = v.strip()

    ov("YT_CLIENT_ID", "client_id")
    ov("YT_CLIENT_SECRET", "client_secret")
    ov("YT_REFRESH_TOKEN", "refresh_token")
    ov("GEMINI_API_KEY", "gemini_api_key")
    ov("HF_TOKEN", "hf_token")
    ov("PEXELS_API_KEY", "pexels_api_key")

    # Defaults
    cfg.setdefault("video_length_sec", 15)
    cfg.setdefault("target_resolution", [1080, 1920])
    cfg.setdefault("visibility", "public")
    cfg.setdefault("pexels_query", ["nature", "space", "city"])
    cfg.setdefault("video_title_template", "AI Shorts - {prompt}")
    cfg.setdefault("video_description_template", "Generated automatically with AI.\nPrompt: {prompt}")
    cfg.setdefault("video_tags", ["AI", "shorts", "trending"])
    return cfg


CFG = load_config()
TARGET_W, TARGET_H = CFG["target_resolution"]
TARGET_RATIO = TARGET_W / TARGET_H


# ---------- Text generation (Prompt/Title/Desc) ----------
def gen_prompt_title_desc() -> Tuple[str, str, str]:
    """Priority: Gemini → HF text → simple fallback. Returns (prompt, title, desc)."""
    topic = random.choice(CFG.get("pexels_query", ["nature", "space", "city"]))

    # 1) Gemini
    if CFG.get("gemini_api_key"):
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Create a short, catchy 6–10 word idea for a vertical YouTube Short about {topic}. "
                                f"Return ONLY the idea text, no quotes."
                    }]
                }]
            }
            r = requests.post(url, params={"key": CFG["gemini_api_key"]}, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            prompt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean one-liner
            prompt = " ".join(prompt.replace("\n", " ").split())
            title = CFG["video_title_template"].format(prompt=prompt)
            desc = CFG["video_description_template"].format(prompt=prompt)
            return prompt, title, desc
        except Exception as e:
            print("⚠️ Gemini failed:", e)

    # 2) HuggingFace (text generation)
    if CFG.get("hf_token"):
        try:
            headers = {"Authorization": f"Bearer {CFG['hf_token']}"}
            inputs = (f"Give a short, catchy 6-10 word idea for a vertical YouTube Short about {topic}. "
                      f"Return only the idea text.")
            r = requests.post(
                "https://api-inference.huggingface.co/models/google/flan-t5-large",
                headers=headers,
                json={"inputs": inputs, "parameters": {"max_new_tokens": 32}},
                timeout=45
            )
            r.raise_for_status()
            out = r.json()
            # HF returns list of dicts with 'generated_text'
            if isinstance(out, list) and out and "generated_text" in out[0]:
                prompt = out[0]["generated_text"].strip()
            else:
                prompt = str(out)[:60]
            prompt = " ".join(prompt.replace("\n", " ").split())
            title = CFG["video_title_template"].format(prompt=prompt)
            desc = CFG["video_description_template"].format(prompt=prompt)
            return prompt, title, desc
        except Exception as e:
            print("⚠️ HF text generation failed:", e)

    # 3) Simple fallback
    prompt = f"Beautiful {topic} scenes"
    title = CFG["video_title_template"].format(prompt=prompt)
    desc = CFG["video_description_template"].format(prompt=prompt)
    return prompt, title, desc


# ---------- Download helpers ----------
def download_stream(url: str, out_path: Path, timeout=120) -> Path:
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    return out_path


# ---------- Pexels video (1st visual preference) ----------
def get_pexels_video(out_file="assets_pexels.mp4") -> Optional[str]:
    key = CFG.get("pexels_api_key")
    if not key:
        return None
    try:
        q = random.choice(CFG.get("pexels_query", ["nature"]))
        url = f"https://api.pexels.com/videos/search?query={q}&per_page=5"
        data = requests.get(url, headers={"Authorization": key}, timeout=30).json()
        vids = data.get("videos", [])
        if not vids:
            return None

        # pick a random video file link (prefer mp4)
        cand = random.choice(vids)
        files = cand.get("video_files", [])
        # Prefer smaller/SD to avoid slow downloads
        files = [f for f in files if f.get("file_type", "").endswith("mp4")]
        files.sort(key=lambda f: f.get("height", 720))  # pick lower height first
        if not files:
            return None

        link = files[0]["link"]
        out = Path(tempfile.gettempdir()) / out_file
        download_stream(link, out)
        print("✅ Pexels video downloaded:", out)
        return str(out)
    except Exception as e:
        print("⚠️ Pexels failed:", e)
        return None


# ---------- HuggingFace image (2nd visual) ----------
def hf_generate_image(prompt: str, out_file="hf_frame.jpg") -> Optional[str]:
    if not CFG.get("hf_token"):
        return None
    try:
        headers = {"Authorization": f"Bearer {CFG['hf_token']}"}
        r = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2",
            headers=headers, json={"inputs": prompt}, timeout=120
        )
        if r.status_code != 200 or "application/json" in r.headers.get("content-type", ""):
            print("⚠️ HF image error:", r.text[:200])
            return None
        out = Path(tempfile.gettempdir()) / out_file
        out.write_bytes(r.content)
        print("✅ HF image generated:", out)
        return str(out)
    except Exception as e:
        print("⚠️ HF image failed:", e)
        return None


# ---------- Manual image (3rd visual) ----------
def pick_manual_image(folder="images") -> Optional[str]:
    try:
        p = Path(folder)
        files = [f for f in p.iterdir() if f.suffix.lower() in [".png", ".jpg", ".jpeg"]]
        if files:
            choice = str(random.choice(files))
            print("✅ Manual image used:", choice)
            return choice
    except Exception:
        pass
    return None


# ---------- Video build helpers ----------
def crop_to_vertical(clip: VideoFileClip) -> VideoFileClip:
    ratio = clip.w / clip.h
    if abs(ratio - TARGET_RATIO) < 1e-3:
        return clip.resize((TARGET_W, TARGET_H))
    if ratio > TARGET_RATIO:
        # too wide → crop width
        new_w = int(TARGET_RATIO * clip.h)
        x1 = (clip.w - new_w) // 2
        clip = clip.crop(x1=x1, y1=0, x2=x1 + new_w, y2=clip.h)
    else:
        # too tall → crop height
        new_h = int(clip.w / TARGET_RATIO)
        y1 = (clip.h - new_h) // 2
        clip = clip.crop(x1=0, y1=y1, x2=clip.w, y2=y1 + new_h)
    return clip.resize((TARGET_W, TARGET_H))


def ensure_duration(clip: VideoFileClip, target_sec: int) -> VideoFileClip:
    if clip.duration >= target_sec:
        return clip.subclip(0, target_sec)
    reps = math.ceil(target_sec / max(1e-6, clip.duration))
    parts = [clip] * reps
    joined = concatenate_videoclips(parts, method="compose")
    return joined.subclip(0, target_sec)


def add_bgm_if_available(clip):
    music_dir = Path("music")
    if music_dir.exists():
        files = [f for f in music_dir.iterdir() if f.suffix.lower() in [".mp3", ".wav", ".m4a"]]
        if files:
            f = str(random.choice(files))
            try:
                a = AudioFileClip(f).volumex(0.6).subclip(0, clip.duration)
                return clip.set_audio(a)
            except Exception as e:
                print("⚠️ Audio add failed:", e)
    return clip


# ---------- Build visual according to priority ----------
def build_video(prompt: str, out_file="short.mp4") -> str:
    # 1) Pexels video
    pv = get_pexels_video()
    if pv:
        with VideoFileClip(pv) as base:
            v = crop_to_vertical(base)
            v = ensure_duration(v, CFG["video_length_sec"])
            v = add_bgm_if_available(v)
            v.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast")
        return out_file

    # 2) HF image
    img = hf_generate_image(prompt)
    if img:
        ic = ImageClip(img, duration=CFG["video_length_sec"]).resize((TARGET_W, TARGET_H))
        ic = add_bgm_if_available(ic)
        ic.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast")
        return out_file

    # 3) Manual image
    man = pick_manual_image()
    if man:
        ic = ImageClip(man, duration=CFG["video_length_sec"]).resize((TARGET_W, TARGET_H))
        ic = add_bgm_if_available(ic)
        ic.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast")
        return out_file

    # 4) Solid color fallback
    cc = ColorClip((TARGET_W, TARGET_H), color=(0, 255, 128), duration=CFG["video_length_sec"])
    cc = add_bgm_if_available(cc)
    cc.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast")
    return out_file


# ---------- YouTube upload ----------
def youtube_service():
    missing = [k for k in ["client_id", "client_secret", "refresh_token"] if not CFG.get(k)]
    if missing:
        raise RuntimeError(f"❌ Missing YouTube secrets: {', '.join(missing)}")

    creds = Credentials(
        None,
        refresh_token=CFG["refresh_token"],
        client_id=CFG["client_id"],
        client_secret=CFG["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_to_youtube(file_path: str, title: str, description: str, visibility: str):
    yt = youtube_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": CFG.get("video_tags", []),
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(file_path, chunksize=5 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"⬆️ Uploading... {int(status.progress() * 100)}%")
    print("✅ Upload complete. Video ID:", response.get("id"))


# ---------- Entry point: 1 run = 1 video ----------
def main():
    prompt, title, desc = gen_prompt_title_desc()
    print("🧠 Prompt:", prompt)
    out_file = "output_short.mp4"
    out_path = build_video(prompt, out_file)
    upload_to_youtube(out_path, title, desc, CFG["visibility"])


if _name_ == "_main_":
    main()
