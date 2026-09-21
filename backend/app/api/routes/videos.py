from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas.frame import FrameExtractionResponse
from app.schemas.video import VideoUploadResponse
from app.services.frame_extraction_service import FrameExtractionService
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


@router.get(
    "/videos/{video_id}/frames",
    response_model=FrameExtractionResponse,
)
async def get_frame_manifest(video_id: str) -> FrameExtractionResponse:
    try:
        return FrameExtractionService().load_manifest(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/videos/{video_id}/stream",
)
async def stream_video(video_id: str) -> FileResponse:
    try:
        video_path, filename = FrameExtractionService()._resolve_video_path(video_id)
        if not video_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        return FileResponse(path=str(video_path), media_type="video/mp4", filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/videos/{video_id}/overlay",
)
async def get_overlay_video(video_id: str) -> FileResponse:
    fe = FrameExtractionService()
    overlay_path = (
        fe.root_dir / "sample-data" / "kinematic-inspection" / video_id / "overlay_video.mp4"
    )
    if not overlay_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Overlay video has not been generated yet for video id '{video_id}'.",
        )
    return FileResponse(
        path=str(overlay_path),
        media_type="video/mp4",
        filename="overlay_video.mp4",
    )

