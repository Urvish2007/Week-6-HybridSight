import os
from langchain_core.tools import tool
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# NOTE: Groq deprecates/rotates vision-capable model IDs frequently
# (llama-3.2-11b-vision-preview and several Llama-4 IDs have already been
# sunset as of mid-2026). Keep this in an env var so you can swap it
# without touching code. Check https://console.groq.com/docs/vision and
# https://console.groq.com/docs/deprecations for the current model before
# you deploy.
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def _describe_image_impl(image_data: str) -> str:
    """Actual implementation, callable directly from app.py (bypassing the
    agent's tool-calling) so we never ask the LLM to copy a giant base64
    string verbatim into a tool argument."""
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail. Extract any relevant text, names, or key elements."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            }],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not process the image: {e}"


@tool
def describe_image(image_data: str) -> str:
    """Describe the content of an image. Input must be a base64 data URI
    (e.g. 'data:image/jpeg;base64,...'). NOTE: in this app, image
    descriptions are generated up front in app.py before the agent runs,
    so the agent normally won't need to call this itself — it's kept
    available as a tool for completeness / future direct image queries."""
    return _describe_image_impl(image_data)