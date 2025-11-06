"""
Image upload endpoint for vision-enabled chat.
Accepts screenshots, charts, console outputs for analysis.
"""
import os
import uuid
import time
import logging
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat"])

# Upload configuration
UPLOAD_DIR = Path("/tmp/infrazen-uploads")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_TTL_SECONDS = 3600  # 1 hour

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_old_images():
    """Background task: Delete images older than IMAGE_TTL_SECONDS."""
    try:
        current_time = time.time()
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > IMAGE_TTL_SECONDS:
                    file_path.unlink()
                    logger.debug(f"Cleaned up old image: {file_path.name}")
    except Exception as e:
        logger.error(f"Error cleaning up old images: {e}")


def validate_image(file: UploadFile) -> None:
    """Validate uploaded file type and size."""
    # Check extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check size (read first chunk to verify it's not empty, then seek back)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )


@router.post("/upload")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict:
    """
    Upload an image for vision analysis.
    
    Returns:
        {
            "image_id": "uuid",
            "filename": "original.png",
            "size": 12345,
            "expires_in": 3600
        }
    """
    try:
        # Validate file
        validate_image(file)
        
        # Generate unique ID and save path
        image_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower()
        save_path = UPLOAD_DIR / f"{image_id}{file_ext}"
        
        # Save file to disk
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Uploaded image: {image_id}{file_ext} ({len(contents)} bytes)")
        
        # Schedule cleanup task
        background_tasks.add_task(cleanup_old_images)
        
        return {
            "image_id": image_id,
            "filename": file.filename,
            "size": len(contents),
            "expires_in": IMAGE_TTL_SECONDS
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload image")


@router.get("/image/{image_id}")
async def get_image_info(image_id: str) -> Dict:
    """
    Check if an uploaded image still exists.
    
    Returns:
        {
            "exists": true,
            "size": 12345,
            "age_seconds": 123
        }
    """
    try:
        # Find file with any allowed extension
        for ext in ALLOWED_EXTENSIONS:
            file_path = UPLOAD_DIR / f"{image_id}{ext}"
            if file_path.exists():
                stats = file_path.stat()
                age = time.time() - stats.st_mtime
                return {
                    "exists": True,
                    "size": stats.st_size,
                    "age_seconds": int(age),
                    "expires_in": max(0, IMAGE_TTL_SECONDS - int(age))
                }
        
        return {"exists": False}
        
    except Exception as e:
        logger.error(f"Error checking image: {e}")
        raise HTTPException(status_code=500, detail="Failed to check image")


def get_image_path(image_id: str) -> Path:
    """
    Get the file path for an uploaded image.
    Raises HTTPException if image not found.
    """
    for ext in ALLOWED_EXTENSIONS:
        file_path = UPLOAD_DIR / f"{image_id}{ext}"
        if file_path.exists():
            return file_path
    
    raise HTTPException(status_code=404, detail=f"Image {image_id} not found or expired")

