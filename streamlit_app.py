import streamlit as st
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import tempfile
import numpy as np
import os
import textwrap

# 🩹 Pillow compatibility patch
from PIL import Image as PILImage
if not hasattr(PILImage, 'ANTIALIAS'):
    PILImage.ANTIALIAS = PILImage.Resampling.LANCZOS

# Settings
MAX_CHARS = 400
FRAME_SKIP = 2
OVERLAY_SCALE = 0.5

def generate_typewriter_clips(text, duration, size=(640, 480), color='white', font_path="DejaVuSans-Bold.ttf"):
    width, height = size
    scaled_size = (int(width * OVERLAY_SCALE), int(height * OVERLAY_SCALE))
    font_size = int(scaled_size[0] * 0.05)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    usable_width = max(scaled_size[0] - 40, 100)
    avg_char_width = max(font_size // 2, 1)
    max_chars_per_line = max(1, usable_width // avg_char_width)

    wrapped_lines = textwrap.wrap(text, width=max_chars_per_line)
    full_text = "\n".join(wrapped_lines)[:MAX_CHARS]

    num_chars = len(full_text)
    char_duration = duration / max(1, num_chars // FRAME_SKIP)
    clips = []

    for i in range(1, num_chars + 1, FRAME_SKIP):
        img = Image.new('RGBA', scaled_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        current_text = full_text[:i]
        lines = current_text.split("\n")
        total_text_height = sum([
            font.getbbox(line)[3] if line.strip() else font_size // 2 for line in lines
        ])
        y = (scaled_size[1] - total_text_height) // 2

        for line in lines:
            if not line.strip():
                y += font_size // 2
                continue
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (scaled_size[0] - line_width) // 2

            outline_color = "black"
            outline_thickness = 2
            for dx in [-outline_thickness, 0, outline_thickness]:
                for dy in [-outline_thickness, 0, outline_thickness]:
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), line, font=font, fill=outline_color)

            draw.text((x, y), line, font=font, fill=color)
            y += bbox[3] - bbox[1]

        # Resize frame back to full size
        img = img.resize(size, resample=PILImage.Resampling.LANCZOS)
        frame = np.array(img)
        clip = ImageClip(frame, ismask=False).set_duration(char_duration)
        clips.append(clip)

    return clips

def overlay_text_on_video(input_path, output_path, text, animation_duration):
    try:
        video = VideoFileClip(input_path)

        # 🔧 Resize video height to 720px for safety
        video = video.resize(height=720)

        video_size = video.size
        text_clips = generate_typewriter_clips(text, animation_duration, size=video_size)
        text_anim = concatenate_videoclips(text_clips)

        if video.duration > animation_duration:
            last = text_clips[-1].set_duration(video.duration - animation_duration)
            text_anim = concatenate_videoclips([text_anim, last])

        text_anim = text_anim.set_position('center').set_start(0)
        final = CompositeVideoClip([video, text_anim])
        final.write_videofile(output_path, codec='libx264', fps=video.fps)

    except Exception as e:
        raise RuntimeError(f"Video generation failed: {e}")

# Streamlit UI
st.title("📝 Typewriter Text on Video (Optimized & Safe)")

uploaded_file = st.file_uploader("Upload a video (.mp4)", type=["mp4"])
text_input = st.text_area("Enter text for animation (max 400 characters)")
duration = st.slider("Text animation duration (seconds)", 1, 20, 5)

if uploaded_file and text_input:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
        temp_input.write(uploaded_file.read())
        temp_input.flush()
        input_path = temp_input.name

    if os.path.getsize(input_path) == 0:
        st.error("❌ Uploaded video file is empty or corrupted.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output:
            output_path = temp_output.name

        with st.spinner("🔄 Generating video... Please wait."):
            try:
                overlay_text_on_video(input_path, output_path, text_input, duration)
                st.success("✅ Video generated successfully!")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button("⬇️ Download Video", f, file_name="output_video.mp4")
            except Exception as e:
                st.error(f"❌ Error: {e}")
