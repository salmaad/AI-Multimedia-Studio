
import os
import re
import json
import time
import hashlib
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from google import genai

# MoviePy 2.x imports
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from asset_gen import generate_image


# ==================================================
# 1. CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Prompt2Video | AI Multimedia Studio",
    page_icon="🎬",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "video_projects"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1280
HEIGHT = 720
FPS = 24

GEMINI_MODEL = "gemini-3.8-flash"


# ==================================================
# 2. USER INTERFACE
# ==================================================

st.title("🎬 Prompt2Video — AI Multimedia Studio")

st.caption(
    "Transform an idea into a narrated video with "
    "scene-specific visuals, subtitles, and storytelling."
)

with st.sidebar:
    st.header("Video settings")

    api_key = st.text_input(
        "Gemini API key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
    )

    topic = st.text_area(
        "What should your video explain?",
        value="How artificial intelligence is changing education",
        height=120,
    )

    video_format = st.selectbox(
        "Video format",
        [
            "YouTube Explainer",
            "TikTok / Shorts",
            "E-Learning Capsule",
            "Marketing Promo",
        ],
    )

    tone = st.selectbox(
        "Narration tone",
        [
            "Engaging & Energetic",
            "Professional & Educational",
            "Dramatic & Cinematic",
            "Casual & Friendly",
        ],
    )

    duration_target = st.select_slider(
        "Target duration",
        options=[30, 45, 60],
        value=45,
        format_func=lambda value: f"{value} seconds",
    )

    use_stable_diffusion = st.checkbox(
        "Use local Stable Diffusion",
        value=False,
        help=(
            "Local image generation can be slow on a CPU. "
            "The fallback generator creates illustrated backgrounds."
        ),
    )

    generate_script_btn = st.button(
        "1. Generate script",
        type="primary",
        use_container_width=True,
    )


# ==================================================
# 3. GEMINI SCRIPT GENERATION
# ==================================================

def generate_video_script(
    topic,
    video_format,
    tone,
    duration,
    api_key,
):
    client = genai.Client(api_key=api_key.strip())

    prompt = f"""
You are a professional multimedia video scriptwriter.

Create a video based on the following information:

Topic: {topic}
Format: {video_format}
Narration tone: {tone}
Target duration: approximately {duration} seconds.

Return a valid JSON object using exactly this structure:

{{
  "title": "An engaging title",
  "format": "{video_format}",
  "total_estimated_duration": "{duration} seconds",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_title": "Scene title",
      "visual_cue": "Detailed image-generation prompt in English",
      "voice_over": "The narration spoken during this scene"
    }}
  ]
}}

Requirements:
- Generate 4 to 6 scenes.
- Make every scene visually DISTINCT from the others.
- Describe the setting, objects, people, lighting, colors and composition.
- Make each visual_cue a self-contained image prompt.
- Each visual must illustrate the specific narration of its scene.
- Avoid repeating the same setting or composition across scenes.
- Do not request text, subtitles, logos or watermarks in images.
- Keep narration concise enough for the requested duration.
- Use natural, informative language.
- Return JSON only, without Markdown fences.
"""

    last_error = None

    for attempt in range(3):
        try:
            response = client.interactions.create(
                model=GEMINI_MODEL,
                input=prompt,
                generation_config={
                    "thinking_level": "low",
                },
            )

            response_text = (response.output_text or "").strip()

            if not response_text:
                raise ValueError("Gemini returned an empty response.")

            # Remove optional Markdown code fences.
            response_text = re.sub(
                r"^```(?:json)?\s*",
                "",
                response_text,
                flags=re.IGNORECASE,
            )
            response_text = re.sub(
                r"\s*```$",
                "",
                response_text,
            )

            data = json.loads(response_text)

            if not isinstance(data, dict):
                raise ValueError("The generated script is not a JSON object.")

            scenes = data.get("scenes")

            if not isinstance(scenes, list) or not scenes:
                raise ValueError("Gemini did not return any scenes.")

            scenes = scenes[:6]

            for index, scene in enumerate(scenes, start=1):
                if not isinstance(scene, dict):
                    raise ValueError(f"Scene {index} is invalid.")

                # Normalize possible alternative field names.
                scene["visual_cue"] = (
                    scene.get("visual_cue")
                    or scene.get("visual_prompt")
                    or scene.get("image_prompt")
                    or scene.get("visual")
                    or ""
                ).strip()

                scene["voice_over"] = (
                    scene.get("voice_over")
                    or scene.get("narration")
                    or scene.get("voiceover")
                    or ""
                ).strip()

                if not scene["visual_cue"]:
                    raise ValueError(
                        f"Scene {index} has no visual description."
                    )

                if not scene["voice_over"]:
                    raise ValueError(
                        f"Scene {index} has no narration."
                    )

                scene["scene_number"] = index

            data["scenes"] = scenes
            data.setdefault("title", topic[:80])
            data.setdefault("format", video_format)
            data["total_estimated_duration"] = f"{duration} seconds"

            return data

        except Exception as exc:
            last_error = exc

            if attempt < 2:
                time.sleep(attempt + 1)

    raise RuntimeError(
        f"Script generation failed after 3 attempts: {last_error}"
    )


# ==================================================
# 4. LOCAL TEXT-TO-SPEECH
# ==================================================

def generate_narration(text, output_path):
    import pyttsx3

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine = None

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()

    except Exception as exc:
        raise RuntimeError(
            f"Could not generate narration: {exc}"
        ) from exc

    finally:
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError(
            f"No usable audio file was generated: {output_path}"
        )

    return output_path


# ==================================================
# 5. SUBTITLE GENERATION
# ==================================================

def load_font(size):
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue

    return ImageFont.load_default()


def create_subtitle_image(text, output_path):
    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(image)
    font = load_font(34)

    # Wrap the text to fit the subtitle panel.
    lines = []
    current_line = ""

    for word in text.split():
        candidate = f"{current_line} {word}".strip()

        text_width = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )[2]

        if text_width > WIDTH - 180 and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate

    if current_line:
        lines.append(current_line)

    # Keep the subtitle panel readable.
    lines = lines[-3:]

    line_height = 45
    panel_height = len(lines) * line_height + 34
    panel_top = HEIGHT - panel_height - 35

    draw.rounded_rectangle(
        (
            65,
            panel_top,
            WIDTH - 65,
            HEIGHT - 35,
        ),
        radius=20,
        fill=(10, 15, 25, 210),
    )

    for index, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]

        x = (WIDTH - text_width) // 2
        y = panel_top + 17 + index * line_height

        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)

    return output_path


# ==================================================
# 6. HELPERS
# ==================================================

def safe_name(value):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    return value.strip("_")[:50] or "video"


def create_project_id(data):
    raw = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:12]


# ==================================================
# 7. VIDEO RENDERING — MOVIEPY 2.x
# ==================================================

def render_full_video(
    script_data,
    output_dir,
    use_stable_diffusion=False,
    target_duration=45,
):
    output_dir = Path(output_dir).resolve()

    images_dir = output_dir / "images"
    audio_dir = output_dir / "audio"
    subtitles_dir = output_dir / "subtitles"

    for directory in (output_dir, images_dir, audio_dir, subtitles_dir):
        directory.mkdir(parents=True, exist_ok=True)

    scenes = script_data.get("scenes", [])

    if not scenes:
        raise ValueError("The script contains no scenes.")

    scene_clips = []
    audio_clips = []
    final_video = None

    target_scene_duration = target_duration / len(scenes)

    try:
        for index, scene in enumerate(scenes, start=1):
            st.write(f"Preparing scene {index} of {len(scenes)}...")

            # Use the exact fields returned by Gemini.
            visual_prompt = (
                scene.get("visual_cue")
                or scene.get("visual_prompt")
                or scene.get("image_prompt")
                or scene.get("visual")
                or f"Cinematic illustration for scene {index}"
            ).strip()

            narration = (
                scene.get("voice_over")
                or scene.get("narration")
                or scene.get("voiceover")
                or ""
            ).strip()

            if not visual_prompt or not narration:
                raise ValueError(
                    f"Scene {index} is missing its image prompt or narration."
                )

            # Each scene has its OWN image filename.
            image_path = images_dir / f"scene_{index:02d}.jpg"

            # Regenerate the scene image rather than reusing a prior file.
            generate_image(
                prompt=visual_prompt,
                output_path=str(image_path),
                use_stable_diffusion=use_stable_diffusion,
                resolution=(WIDTH, HEIGHT),
            )

            if not image_path.exists() or image_path.stat().st_size == 0:
                raise RuntimeError(
                    f"No background image was generated for scene {index}."
                )

            # Normalize every image to the video resolution.
            with Image.open(image_path) as img:
                normalized = img.convert("RGB").resize(
                    (WIDTH, HEIGHT),
                    Image.Resampling.LANCZOS,
                )
                normalized.save(image_path, quality=92)

            # Create independent narration files.
            audio_path = audio_dir / f"scene_{index:02d}.wav"

            generate_narration(
                narration,
                audio_path,
            )

            audio_clip = AudioFileClip(str(audio_path))
            audio_clips.append(audio_clip)

            # Never shorten narration to fit the target duration.
            scene_duration = max(
                target_scene_duration,
                audio_clip.duration,
            )

            # Each clip loads its own background image.
            background_clip = (
                ImageClip(str(image_path))
                .with_duration(scene_duration)
            )

            subtitle_path = (
                subtitles_dir / f"scene_{index:02d}.png"
            )

            create_subtitle_image(
                narration,
                subtitle_path,
            )

            subtitle_clip = (
                ImageClip(str(subtitle_path), transparent=True)
                .with_duration(scene_duration)
                .with_position(("center", "center"))
            )

            # Compose the background and subtitle overlay.
            composed_scene = CompositeVideoClip(
                [background_clip, subtitle_clip],
                size=(WIDTH, HEIGHT),
            ).with_duration(scene_duration)

            # Attach the narration for this particular scene.
            composed_scene = composed_scene.with_audio(audio_clip)

            scene_clips.append(composed_scene)

            st.success(
                f"Scene {index} prepared: {image_path.name}"
            )

        # Concatenate all distinct scenes in order.
        final_video = concatenate_videoclips(
            scene_clips,
            method="compose",
        )

        output_path = output_dir / "final_video.mp4"

        final_video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger="bar",
        )

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("The MP4 file was not created successfully.")

        return output_path

    finally:
        if final_video is not None:
            final_video.close()

        for clip in scene_clips:
            try:
                clip.close()
            except Exception:
                pass

        for clip in audio_clips:
            try:
                clip.close()
            except Exception:
                pass


# ==================================================
# 8. MAIN WORKFLOW
# ==================================================

if generate_script_btn:
    if not api_key.strip():
        st.error("Please enter your Gemini API key.")

    elif not topic.strip():
        st.error("Please enter a video topic.")

    else:
        try:
            with st.spinner("Generating your video script..."):
                data = generate_video_script(
                    topic=topic,
                    video_format=video_format,
                    tone=tone,
                    duration=duration_target,
                    api_key=api_key,
                )

            st.session_state["script_data"] = data
            st.success("Script generated successfully!")

        except Exception as exc:
            st.error(f"Script generation failed: {exc}")


if "script_data" in st.session_state:
    data = st.session_state["script_data"]

    st.divider()
    st.header(data.get("title", "Your video"))

    st.caption(
        f"Format: {data.get('format', video_format)} · "
        f"Target duration: {duration_target} seconds"
    )

    with st.expander("Review generated script", expanded=True):
        st.json(data)

        st.download_button(
            "Download script JSON",
            data=json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="video_script.json",
            mime="application/json",
        )

    if st.button(
        "2. Generate complete video 🎬",
        type="primary",
    ):
        project_id = create_project_id(data)
        project_dir = CACHE_DIR / project_id

        try:
            with st.spinner(
                "Generating scene images, narration, and video..."
            ):
                output_path = render_full_video(
                    script_data=data,
                    output_dir=project_dir,
                    use_stable_diffusion=use_stable_diffusion,
                    target_duration=duration_target,
                )

            st.success("Your video is ready!")
            st.video(str(output_path))

            with open(output_path, "rb") as video_file:
                st.download_button(
                    "Download complete MP4",
                    data=video_file.read(),
                    file_name=(
                        f"{safe_name(data.get('title', 'video'))}.mp4"
                    ),
                    mime="video/mp4",
                )

            # Show the generated images for quick inspection.
            with st.expander("View generated scene backgrounds"):
                columns = st.columns(2)

                for index, scene in enumerate(data["scenes"]):
                    image_path = (
                        project_dir
                        / "images"
                        / f"scene_{index + 1:02d}.jpg"
                    )

                    with columns[index % 2]:
                        st.image(
                            str(image_path),
                            caption=scene.get(
                                "scene_title",
                                f"Scene {index + 1}",
                            ),
                            use_container_width=True,
                        )

        except Exception as exc:
            st.error(f"Video generation failed: {exc}")
            st.exception(exc)
