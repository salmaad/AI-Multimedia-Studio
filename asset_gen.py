
import hashlib
import random
from pathlib import Path

from PIL import Image, ImageDraw


_pipeline = None
_pipeline_device = None


def _load_stable_diffusion():
    """
    Load the model only when requested.

    The first load may require an internet connection to download
    model files unless the model is already cached locally.
    """
    global _pipeline, _pipeline_device

    if _pipeline is not None:
        return _pipeline

    import torch
    from diffusers import StableDiffusionPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    model_id = "OFA-Sys/small-stable-diffusion-v0"

    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
    )

    if device == "cuda":
        pipe = pipe.to(device)
    else:
        # CPU inference can be slow, but avoids requiring a GPU.
        pipe = pipe.to("cpu")
        pipe.enable_attention_slicing()

    _pipeline = pipe
    _pipeline_device = device
    return _pipeline


def _create_local_visual(prompt, output_path, resolution):
    """
    Offline fallback: create an illustrated background locally.
    This is a placeholder visual, not an AI-generated photograph.
    """
    width, height = resolution

    seed = int(
        hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8],
        16,
    )
    rng = random.Random(seed)

    image = Image.new("RGB", (width, height))
    pixels = image.load()

    # Dark blue/purple cinematic gradient.
    top = (12, 24, 53)
    bottom = (48, 28, 75)

    for y in range(height):
        ratio = y / max(height - 1, 1)

        color = tuple(
            int(top[channel] * (1 - ratio) + bottom[channel] * ratio)
            for channel in range(3)
        )

        for x in range(width):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image, "RGBA")

    # Soft decorative circles and geometric elements.
    for _ in range(28):
        radius = rng.randint(
            max(8, width // 100),
            max(15, width // 18),
        )
        x = rng.randint(-radius, width + radius)
        y = rng.randint(-radius, height + radius)

        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(
                rng.randint(65, 130),
                rng.randint(95, 180),
                rng.randint(150, 230),
                rng.randint(12, 40),
            ),
        )

    # Abstract luminous lines.
    for _ in range(12):
        x1 = rng.randint(0, width)
        y1 = rng.randint(0, height)
        x2 = x1 + rng.randint(-width // 4, width // 4)
        y2 = y1 + rng.randint(-height // 4, height // 4)

        draw.line(
            (x1, y1, x2, y2),
            fill=(130, 180, 255, 45),
            width=rng.randint(1, 4),
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, quality=92)
    return output_path


def generate_image(
    prompt,
    output_path,
    use_stable_diffusion=False,
    resolution=(1280, 720),
):
    """
    Generate an image locally.

    When Stable Diffusion is enabled, use the local model.
    If generation fails, create a local illustrated fallback.
    No stock-image services or online image search are used.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if use_stable_diffusion:
        try:
            import torch

            pipe = _load_stable_diffusion()

            with torch.inference_mode():
                result = pipe(
                    prompt=(
                        f"{prompt}, cinematic composition, "
                        "coherent scene, high quality, "
                        "no text, no lettering, no watermark"
                    ),
                    num_inference_steps=15,
                    guidance_scale=6.0,
                    height=512,
                    width=768,
                )

            image = result.images[0].convert("RGB")
            image = image.resize(
                resolution,
                Image.Resampling.LANCZOS,
            )
            image.save(output_path, quality=92)
            return output_path

        except Exception as exc:
            print(f"Local Stable Diffusion failed: {exc}")
            print("Using a local illustrated fallback instead.")

    return _create_local_visual(
        prompt=prompt,
        output_path=output_path,
        resolution=resolution,
    )
