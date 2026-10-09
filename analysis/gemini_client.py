"""Thin Gemini client wrapper. Reads GEMINI_API_KEY from .env at the project root."""
import mimetypes
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemini-3.1-flash-lite"


class MissingApiKeyError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            f"GEMINI_API_KEY is not set in {PROJECT_ROOT / '.env'}. Add a line "
            f"GEMINI_API_KEY=<your key> and try again."
        )
    return genai.Client(api_key=api_key)


def generate_from_image(image_path: Path, prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Sends one image + a text prompt to Gemini and returns the text response."""
    client = get_client()
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    image_part = types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)
    response = client.models.generate_content(
        model=model,
        contents=[image_part, prompt],
    )
    return (response.text or "").strip()


def generate_json_from_image(
    image_path: Path, prompt: str, model: str = DEFAULT_MODEL, max_output_tokens: int = 4096,
) -> str:
    """Same as generate_from_image but asks Gemini to constrain output to JSON.

    max_output_tokens is set well above the default since structured multi-field
    JSON responses (creative_root/mechanism/visual_motif/applicability/story/
    storyboard) were getting cut off mid-string at the SDK's default cap.
    """
    client = get_client()
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    image_part = types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)
    response = client.models.generate_content(
        model=model,
        contents=[image_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=max_output_tokens,
        ),
    )
    return (response.text or "").strip()
