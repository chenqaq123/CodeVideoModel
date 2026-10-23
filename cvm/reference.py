"""GPT-Image-2 strict appearance transfer or text-guided reference generation."""
import base64
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from PIL import Image

from . import IMAGE_MODEL

ENDPOINT = "https://openrouter.ai/api/v1/images"
REFERENCE_SIZE = (1536, 864)


def payload(frame: Path, *, text_prompt: str | None = None) -> dict:
    encoded = base64.b64encode(frame.read_bytes()).decode("ascii")
    prompts = Path(__file__).resolve().parents[1] / "prompts"
    if text_prompt is not None:
        if not text_prompt.strip():
            raise ValueError("The text prompt must not be empty.")
        prompt = (prompts / "reference_guided.txt").read_text().strip()
        prompt += "\n\nScene intent:\n" + text_prompt.strip()
    else:
        prompt = (prompts / "reference.txt").read_text().strip()
    with Image.open(frame) as image:
        if image.format not in ("PNG", "JPEG", "WEBP"):
            raise ValueError("Expected a PNG, JPEG or WebP reference.")
        mime = Image.MIME[image.format]
    return {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "input_references": [{"type": "image_url", "image_url": {
            "url": f"data:{mime};base64,{encoded}"}}],
        "size": f"{REFERENCE_SIZE[0]}x{REFERENCE_SIZE[1]}",
        "quality": "medium",
        "n": 1,
        "provider": {"only": ["openai"], "allow_fallbacks": False},
    }


def generate(frame: Path, output: Path, *, text_prompt: str | None = None) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to repeat a paid edit over {output}")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Set OPENROUTER_API_KEY in your environment.")
    request_data = payload(frame, text_prompt=text_prompt)
    expected_size = tuple(int(value) for value in request_data["size"].split("x"))
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(request_data).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GPT-Image-2 request failed: HTTP {error.code}") from error
    data = result.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise ValueError("GPT-Image-2 returned no image.")
    encoded = data[0].get("b64_json")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("GPT-Image-2 returned no base64 image.")
    raw = base64.b64decode(encoded, validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        if image.size != expected_size:
            raise ValueError(
                f"GPT-Image-2 returned {image.width}x{image.height}; "
                f"requested {expected_size[0]}x{expected_size[1]}. No resizing was applied."
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            image.convert("RGB").save(stream, format="PNG")
