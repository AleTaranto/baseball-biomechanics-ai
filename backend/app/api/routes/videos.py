from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.video import VideoUploadResponse
from app.services.video_ingestion_service import VideoIngestionService

router = APIRouter(prefix="/api/v1", tags=["videos"])


@router.post(
    "/videos/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
    try:
        return VideoIngestionService().store_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
