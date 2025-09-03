import os
CFG["client_id"] = os.getenv("YT_CLIENT_ID", CFG.get("client_id"))
CFG["client_secret"] = os.getenv("YT_CLIENT_SECRET", CFG.get("client_secret"))
CFG["refresh_token"] = os.getenv("YT_REFRESH_TOKEN", CFG.get("refresh_token"))
import os, json, random, subprocess
from typing import Optional
import requests
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, vfx
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def log(m): print(m, flush=True)

def ensure_dirs():
    for d in ["images","music","outputs","cache"]:
        os.makedirs(d, exist_ok=True)

with open("config.json","r",encoding="utf-8") as f:
    CFG = json.load(f)

def fetch_pexels_video() -> Optional[str]:
    key = os.environ.get("PEXELS_API_KEY","").strip()
    if not key: return None
    q = random.choice(CFG.get("pexels_query",["nature"]))
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": key}
    try:
        r = requests.get(url, headers=headers, params={"query": q, "per_page": 30}, timeout=30)
        if r.status_code != 200: return None
        vids = r.json().get("videos",[])
        random.shuffle(vids)
        for v in vids:
            for vf in v.get("video_files",[]):
                link = vf.get("link")
                if not link: continue
                try:
                    path = os.path.join("cache", f"pexels_{v.get('id')}.mp4")
                    rr = requests.get(link, timeout=60)
                    if rr.status_code == 200:
                        open(path,"wb").write(rr.content)
                        return path
                except Exception: pass
        return None
    except Exception:
        return None

def generate_ai_image() -> Optional[str]:
    key = os.environ.get("HUGGINGFACE_API_KEY","").strip()
    if not key: return None
    prompts = [
        "Neon cyberpunk street, rainy reflections, ultra-detailed",
        "Dreamy sunrise mountains above clouds, golden hour",
        "Abstract liquid gradient waves, soothing colors",
        "Cute astronaut with cat floating in space"
    ]
    url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json={"inputs": random.choice(prompts)}, timeout=60)
        if r.status_code == 200 and r.content:
            out = os.path.join("cache","ai.jpg")
            open(out,"wb").write(r.content)
            return out
        return None
    except Exception:
        return None

def pick_manual_image() -> Optional[str]:
    imgs = [os.path.join("images",f) for f in os.listdir("images") if f.lower().endswith((".jpg",".jpeg",".png"))]
    if not imgs: return None
    return random.choice(imgs)

def pick_local_music() -> Optional[str]:
    mp3s = [os.path.join("music",f) for f in os.listdir("music") if f.lower().endswith(".mp3")]
    return random.choice(mp3s) if mp3s else None

def download_music(search_q: str) -> Optional[str]:
    try:
        outpattern = os.path.join("cache","music.%(ext)s")
        cmd = ["yt-dlp","-x","--audio-format","mp3","--no-playlist","-o",outpattern, search_q]
        log("🎵 yt-dlp: " + " ".join(cmd))
        subprocess.check_call(cmd)
        for f in os.listdir("cache"):
            if f.startswith("music.") and f.endswith(".mp3"):
                return os.path.join("cache", f)
        return None
    except Exception as e:
        log(f"yt-dlp failed: {e}")
        return None

def to_vertical(clip, target=(1080,1920)):
    w,h = clip.size
    tw,th = target
    scale = max(tw/w, th/h)
    clip = clip.resize(scale)
    return clip.fx(vfx.crop, width=tw, height=th, x_center=clip.w/2, y_center=clip.h/2)

def make_video_from_image(img: str, music: str, length: int, target=(1080,1920)) -> str:
    clip = ImageClip(img, duration=length).resize(height=target[1])
    clip = clip.fx(vfx.scroll, w=clip.w, h=clip.h, x_speed=0, y_speed=-10)
    audio = AudioFileClip(music).subclip(0, length)
    out = os.path.join("outputs","short.mp4")
    clip.set_audio(audio).write_videofile(out, fps=30, audio_codec="aac")
    return out

def make_video_from_pexels(video: str, music: str, length: int, target=(1080,1920)) -> str:
    clip = VideoFileClip(video)
    if clip.duration > length: clip = clip.subclip(0, length)
    clip = to_vertical(clip, target=tuple(target))
    audio = AudioFileClip(music).subclip(0, length)
    out = os.path.join("outputs","short.mp4")
    clip.set_audio(audio).write_videofile(out, fps=30, audio_codec="aac")
    return out

def gemini_text(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY","").strip()
    if not key: return "AI Short"
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            params={"key": key},
            headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}]},
            timeout=60
        ).json()
        return r.get("candidates",[{}])[0].get("content",{}).get("parts",[{"text":"AI Short"}])[0].get("text","AI Short")
    except Exception:
        return "AI Short"

def upload_youtube(file_path: str, title: str, desc: str, visibility: str):
    need = ["YT_CLIENT_ID","YT_CLIENT_SECRET","YT_REFRESH_TOKEN"]
    miss = [k for k in need if not os.environ.get(k)]
    if miss: raise RuntimeError("Missing secrets: " + ",".join(miss))
    creds = Credentials.from_authorized_user_info({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "token_uri": "https://oauth2.googleapis.com/token"
    })
    yt = build("youtube","v3",credentials=creds)
    body = {
        "snippet": {
            "title": title[:95],
            "description": desc[:4500],
            "tags": ["shorts","ai","pexels","nocopyright"]
        },
        "status": {"privacyStatus": visibility}
    }
    log("📤 Uploading...")
    yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(file_path)).execute()
    log("✅ Uploaded!")

def main():
    ensure_dirs()
    length = int(CFG.get("video_length_sec",15))
    target = tuple(CFG.get("target_resolution",[1080,1920]))

    music = pick_local_music()
    if not music:
        music = download_music(CFG.get("music_search_query","ytsearch20:No Copyright background music short"))
        if not music: raise RuntimeError("No music found or downloaded.")

    vid = fetch_pexels_video()
    if vid:
        log("🎬 Using Pexels video")
        out = make_video_from_pexels(vid, music, length, target)
        subject = "stunning free stock video"
    else:
        log("🎨 Pexels failed, trying AI image...")
        img = generate_ai_image()
        if not img:
            log("🖼️ AI failed, using manual image...")
            img = pick_manual_image()
            if not img: raise RuntimeError("No image available (AI + manual failed).")
            subject = "beautiful visual from my gallery"
        else:
            subject = "AI generated visual art"
        out = make_video_from_image(img, music, length, target)

    title = gemini_text(f"Create a catchy YouTube Shorts title (<=95 chars) about a {subject}. Include one emoji.")
    desc = gemini_text(f"Write a short YouTube description (1-2 lines) with 5 hashtags about a {subject}. Family friendly.")

    upload_youtube(out, title, desc, CFG.get("visibility","public"))

if __name__ == "__main__":
    main()
