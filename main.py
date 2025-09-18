import os
import random
import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont

# ------------------------------
# Config
# ------------------------------
VIDEO_SIZE = (1080, 1920)
IMAGE_FOLDER = "images"
MUSIC_FOLDER = "music"
QUOTES_FILE = "quotes.txt"
OUTPUT_FILE = "output.mp4"

# ------------------------------
# Helper: Load random quote
# ------------------------------
def load_random_quote():
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        quotes = [line.strip() for line in f if line.strip()]
    return random.choice(quotes)

# ------------------------------
# Helper: Create text clip with PIL
# ------------------------------
def make_text_clip(text, size, duration, fontsize=70):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", fontsize)
    except:
        font = ImageFont.load_default()

    max_width = int(size[0] * 0.8)
    words = text.split(" ")
    lines, line = [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            lines.append(line)
            line = w
    lines.append(line)

    y = size[1] - (len(lines) * (fontsize + 10)) - 150
    for l in lines:
        w = draw.textlength(l, font=font)
        x = (size[0] - w) // 2
        draw.text((x, y), l, font=font, fill="white", stroke_width=2, stroke_fill="black")
        y += fontsize + 10

    np_img = np.array(img)
    return ImageClip(np_img).set_duration(duration)

# ------------------------------
# Main video generator
# ------------------------------
def create_video():
    # Pick random image
    img_file = random.choice(os.listdir(IMAGE_FOLDER))
    img_path = os.path.join(IMAGE_FOLDER, img_file)

    # Pick random music
    music_file = random.choice(os.listdir(MUSIC_FOLDER))
    music_path = os.path.join(MUSIC_FOLDER, music_file)

    # Quote
    quote_text = load_random_quote()

    # Prepare image clip
    img_clip = ImageClip(img_path)
    img_clip = img_clip.resize(height=VIDEO_SIZE[1])
    img_clip = img_clip.crop(width=VIDEO_SIZE[0], height=VIDEO_SIZE[1], x_center=img_clip.w/2, y_center=img_clip.h/2)
    img_clip = img_clip.set_duration(30)

    # Add text
    txt_clip = make_text_clip(quote_text, VIDEO_SIZE, img_clip.duration, fontsize=70)

    # Add background music
    audio_clip = AudioFileClip(music_path).volumex(0.2)

    # Final video
    final = CompositeVideoClip([img_clip, txt_clip])
    final = final.set_audio(audio_clip)

    # Export
    final.write_videofile(OUTPUT_FILE, fps=30, codec="libx264", audio_codec="aac")

    print("✅ Video created:", OUTPUT_FILE)

# ------------------------------
if __name__ == "__main__":
    create_video()
    
