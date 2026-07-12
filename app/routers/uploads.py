"""Image upload endpoint.

Images are stored as base64 data URLs directly on the user/post documents
rather than in an external object store. Trade-off, documented here rather
than scattered across the code: this app runs on Railway's free/hobby tier
with a single MongoDB instance and no budget for an object-storage add-on
(S3, Cloudinary, etc.), so avoiding a second external dependency and its API
keys keeps deployment a one-service affair. The cost is document size, so
every upload is aggressively downsized and re-encoded as JPEG before it's
persisted -- a post image is capped at 1280px on its long edge and a profile
image at 640px, both at quality 82, which keeps typical images in the tens
of KB and comfortably under MongoDB's 16MB document limit even with two
images on a post. If image volume ever grows enough for this to matter,
swap this endpoint's return value for a real object-store URL; every caller
already just treats the result as an opaque image URL string.
"""

import base64
import io

from fastapi import APIRouter, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError

from app.schemas import UploadResponse

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
_MAX_DIMENSIONS = {"post": 1280, "avatar": 640, "cover": 1600}


@router.post("/image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile, kind: str = Query("post", pattern="^(post|avatar|cover)$")
):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image must be under 5MB.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except UnidentifiedImageError:
        raise HTTPException(status_code=422, detail="File is not a valid image.")

    if img.mode not in ("RGB", "L"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    else:
        img = img.convert("RGB")

    max_dim = _MAX_DIMENSIONS[kind]
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=82, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {"data_url": f"data:image/jpeg;base64,{encoded}"}
