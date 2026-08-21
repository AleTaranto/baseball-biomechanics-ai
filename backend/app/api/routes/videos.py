from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.frame import FrameExtractionResponse
from app.schemas.pose import PoseEstimationResponse
from app.schemas.video import VideoUploadResponse
from app.services.frame_extraction_service import FrameExtractionService
from app.services.pose_estimation_service import PoseEstimationService
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


@router.post(
    "/videos/{video_id}/extract-frames",
    response_model=FrameExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_frames(video_id: str) -> FrameExtractionResponse:
    try:
        return FrameExtractionService().extract_frames(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/videos/{video_id}/frames",
    response_model=FrameExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_extracted_frames(video_id: str) -> FrameExtractionResponse:
    try:
        return FrameExtractionService().load_manifest(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/videos/{video_id}/pose-estimation",
    response_model=PoseEstimationResponse,
    status_code=status.HTTP_200_OK,
)
async def estimate_pose(video_id: str) -> PoseEstimationResponse:
    try:
        return PoseEstimationService().estimate_video(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/videos/{video_id}/poses",
    response_model=PoseEstimationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pose_manifest(video_id: str) -> PoseEstimationResponse:
    try:
        return PoseEstimationService().load_manifest(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
