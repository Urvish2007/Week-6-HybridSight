import base64
import mimetypes


def image_to_data_uri(filepath: str) -> str:
    """Converts a local image file to a base64 data URI, detecting the
    real mime type instead of assuming jpeg (fixes PNG/webp uploads being
    mislabeled, which some vision models reject)."""
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"  # reasonable fallback only, not a blind assumption

    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"