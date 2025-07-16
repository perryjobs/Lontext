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

# Built-in font options
FONT_OPTIONS = {
    "DejaVu Sans": {
        "Regular": "DejaVuSans.ttf",
        "Bold": "DejaVuSans-Bold.ttf",
        "Italic": "DejaVuSans-Oblique.ttf"
    },
    "Arial": {
        "Regular": "Arial.ttf",
        "Bold": "Arial Bold.ttf",
        "Italic": "Arial Italic.ttf"
    },
    "Liberation Serif": {
        "Regular": "LiberationSerif-Regular.ttf",
        "Bold": "LiberationSerif-Bold.ttf",
        "Italic": "LiberationSerif-Italic.ttf"
    }
}

MAX_CHARS = 400
FRAME_SKIP = 2
OVERLAY_SCALE = 0.5

def generate_typewriter_clips(text, duration, size, font_path, font_size, text_color, outline_color, outline_thickness):
    width, height = size
    scaled_size = (int(width * OVERLAY_SCALE), int(height * OVERLAY_SCALE))
    scaled_font_size = int(font_size * OVERLAY_SCALE)

    try:
        font = ImageFont.truetype(font_path, scaled_font_size)
    except:
        font = ImageFont.load_default()

    usable_width = max(scaled_size[0] - 40, 100)
    avg_char_width = max(scaled_font_size // 2, 1)
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
            font.getbbox(line)[3] if line.strip() else scaled_font_size // 2 for line in lines
        ])
        y = (scaled_size[1] - total_text_height) // 2

        for line in lines:
            if not line.strip():
                y += scaled_font_size // 2
                continue
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (scaled_size[0] - line_width) // 2

            for dx in range(-outline_thickness, outline_thickness + 1):
                for dy in range(-outline_thickness, outline_thickness + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), line, font=font, fill=outline_color)

            draw.text((x, y), line, font=font, fill=text_color)
            y += bbox[3] - bbox[1]

        img = img.resize(size, resample=PILImage.Resampling.LANCZOS)
        frame = np.array(img)
        clip = ImageClip(frame, ismask=False).set_duration(char_duration)
        clips.append(clip)

    return clips

def overlay_text_on_video(input_path, output_path, text, animation_duration, font_path, font_size, text_color, outline_color, outline_thickness):
    try:
        video = VideoFileClip(input_path)
        video = video.resize(height=720)  # Downscale for memory

        video_size = video.size
        text_clips = generate_typewriter_clips(
            text, animation_duration, size=video_size,
            font_path=font_path, font_size=font_size,
            text_color=text_color, outline_color=outline_color,
            outline_thickness=outline_thickness
        )

        text_anim = concatenate_videoclips(text_clips)
        if video.duration > animation_duration:
            last = text_clips[-1].set_duration(video.duration - animation_duration)
            text_anim = concatenate_videoclips([text_anim, last])

        text_anim = text_anim.set_position('center').set_start(0)
        final = CompositeVideoClip([video, text_anim])
        final.write_videofile(output_path, codec='libx264', fps=video.fps)

    except Exception as e:
        raise RuntimeError(f"Video generation failed: {e}")

# --- Streamlit UI ---
st.title("📝 Typewriter Text on Video (Styled & Safe)")

uploaded_file = st.file_uploader("Upload a video (.mp4)", type=["mp4"])
text_input = st.text_area("Enter text for animation (max 400 characters)")
duration = st.slider("Text animation duration (seconds)", 1, 20, 5)

st.subheader("🖋️ Text Style Options")

# Font selection
selected_font_family = st.selectbox("Font Family", list(FONT_OPTIONS.keys()))
selected_font_weight = st.radio("Font Style", ["Regular", "Bold", "Italic"], horizontal=True)

font_path = FONT_OPTIONS[selected_font_family].get(selected_font_weight, "DejaVuSans.ttf")

font_size = st.slider("Font Size", 20, 100, 48)
text_color = st.color_picker("Text Color", "#FFFFFF")
outline_color = st.color_picker("Outline Color", "#000000")
outline_thickness = st.slider("Outline Thickness", 0, 5, 2)

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

        with st.spinner("🔄 Generating styled video..."):
            try:
                overlay_text_on_video(
                    input_path, output_path, text_input, duration,
                    font_path, font_size, text_color, outline_color, outline_thickness
                )
                st.success("✅ Video generated successfully!")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button("⬇️ Download Video", f, file_name="output_video.mp4")
            except Exception as e:
                st.error(f"❌ Error: {e}")
