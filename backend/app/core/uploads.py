from fastapi import HTTPException, UploadFile

from app.core.config import settings


async def read_capped(file: UploadFile, max_mb: int | None = None) -> bytes:
    """Reads an upload into memory in 1MB chunks, aborting as soon as the size
    cap is exceeded rather than buffering the whole body first -- bounds
    per-request memory to ~max_mb regardless of how large the client claims
    (or actually sends) the file to be."""
    max_mb = max_mb if max_mb is not None else settings.max_image_upload_mb
    max_bytes = max_mb * 1024 * 1024
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail=f"File exceeds {max_mb}MB limit")
        chunks.append(chunk)
    return b"".join(chunks)
