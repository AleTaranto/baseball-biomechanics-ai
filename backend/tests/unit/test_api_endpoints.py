from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.main import app
from app.schemas.bat import BatDetection, BatTrackingResult
from app.schemas.batting import BattingMetricsResult, HandPathMetrics, KinematicSequenceReport
from app.schemas.benchmark import AccuracyMetrics, BenchmarkComparisonReport, BenchmarkRunResult
from app.schemas.contact import ContactDetectionResult, ContactSignalEntry
from app.schemas.pitching import (
    PitchingAnalysisResult,
    PitchingBiomechanicalMetrics,
    PitchingDeliveryWindow,
)
from app.schemas.two_pass import ActionWindow, TwoPassResult
from fastapi.testclient import TestClient

client = TestClient(app)


def test_api_analyze_batting_mocked():
    mock_metrics = BattingMetricsResult(
        recording_id="rec_001",
        source_video_id="mock_vid",
        kinematic_sequence=KinematicSequenceReport(is_proximal_to_distal=True),
        hand_path=HandPathMetrics(),
    )
    with patch(
        "app.api.routes.analysis._get_or_create_movement_and_kinematics"
    ) as mock_get, patch(
        "app.services.swing_segmentation_service.BattingSwingSegmenter.segment",
        return_value=MagicMock(candidate_swings=[]),
    ), patch(
        "app.services.batting_metrics_service.BattingMetricsService.analyze_batting_swing",
        return_value=mock_metrics,
    ):
        mock_get.return_value = (MagicMock(), MagicMock(), MagicMock())
        response = client.post("/api/v1/analysis/batting/mock_vid")
        assert response.status_code == 200
        data = response.json()
        assert data["source_video_id"] == "mock_vid"


def test_api_analyze_pitching_mocked():
    mock_pitch = PitchingAnalysisResult(
        video_id="mock_vid",
        delivery_detected=True,
        delivery_window=PitchingDeliveryWindow(start_frame=0, end_frame=10, duration_seconds=0.33),
        metrics=PitchingBiomechanicalMetrics(handedness="RHP", stride_length_normalized=0.42),
    )
    with patch(
        "app.api.routes.analysis._get_or_create_movement_and_kinematics"
    ) as mock_get, patch(
        "app.services.pitching_analyzer_service.PitchingAnalyzer.analyze_pitch",
        return_value=mock_pitch,
    ):
        mock_get.return_value = (MagicMock(), MagicMock(), MagicMock())
        response = client.post("/api/v1/analysis/pitching/mock_vid?handedness_override=RHP")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["metrics"]["handedness"] == "RHP"


def test_api_bat_tracking_mocked():
    mock_bat = BatTrackingResult(
        video_id="mock_vid",
        detections=[
            BatDetection(
                frame_index=1,
                timestamp_seconds=0.033,
                detected=True,
                barrel_point=(0.5, 0.4),
                handle_point=(0.4, 0.4),
                confidence=0.8,
            )
        ],
        tracking_coverage=0.9,
    )
    with patch(
        "app.api.routes.analysis._get_or_create_movement_and_kinematics"
    ) as mock_get, patch(
        "app.services.bat_tracker_service.ShaftEdgeBatTracker.track",
        return_value=mock_bat,
    ):
        mock_get.return_value = (MagicMock(), MagicMock(), MagicMock())
        response = client.post("/api/v1/analysis/bat-tracking/mock_vid")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["tracking_coverage"] == 0.9


def test_api_contact_detection_mocked():
    mock_contact = ContactDetectionResult(
        video_id="mock_vid",
        contact_frame=8,
        contact_time_seconds=0.26,
        confidence=0.95,
        signals=[
            ContactSignalEntry(
                signal_name="bat_speed_peak",
                estimated_frame=8,
                confidence=0.9,
            )
        ],
    )
    with patch(
        "app.api.routes.analysis._get_or_create_movement_and_kinematics"
    ) as mock_get, patch(
        "app.services.swing_segmentation_service.BattingSwingSegmenter.segment",
        return_value=MagicMock(candidate_swings=[]),
    ), patch(
        "app.services.contact_detector_service.ContactEventDetector.detect_contact",
        return_value=mock_contact,
    ), patch(
        "app.services.bat_tracker_service.ShaftEdgeBatTracker.track",
        return_value=MagicMock(),
    ):
        mock_get.return_value = (MagicMock(), MagicMock(), MagicMock())
        response = client.post("/api/v1/analysis/contact/mock_vid?manual_contact_frame=8")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["contact_frame"] == 8


def test_api_pipeline_run_mocked():
    fake_run_result = {
        "video_id": "mock_vid",
        "source_fps": 30.0,
        "processing_fps": 45.0,
        "processing_mode": "full",
        "total_frames": 30,
        "frames_with_pose": 30,
        "quality_summary_path": "path/quality.json",
        "overlay_video_path": "path/overlay.mp4",
        "batting_metrics_path": "path/batting.json",
        "pitching_result_path": "path/pitching.json",
        "contact_frame": 12,
        "contact_confidence": 0.9,
        "peak_barrel_speed": 15.2,
        "max_shoulder_hip_separation_deg": 35.0,
        "stride_length_normalized": 0.4,
        "arm_slot_angle_deg": 48.0,
        "compute_reduction_percentage": 0.0,
        "action_windows_count": 1,
    }
    with patch("app.api.routes.pipeline.run_pipeline", return_value=fake_run_result):
        response = client.post(
            "/api/v1/pipeline/run/mock_vid",
            json={"processing_mode": "full", "filter_mode": "filtered"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["contact_frame"] == 12
        assert data["stride_length_normalized"] == 0.4


def test_api_pipeline_two_pass_mocked():
    mock_tp = TwoPassResult(
        video_id="mock_vid",
        total_video_frames=50,
        pass1_scanned_frames=13,
        pass2_analyzed_frames=20,
        total_processed_frames=33,
        compute_reduction_percentage=34.0,
        action_windows=[
            ActionWindow(
                start_frame=10,
                end_frame=30,
                start_time_seconds=0.33,
                end_time_seconds=1.0,
                motion_intensity=0.8,
            )
        ],
    )
    with patch(
        "app.services.frame_extraction_service.FrameExtractionService.extract_frames"
    ), patch(
        "app.services.two_pass_pipeline_service.TwoPassPipelineService.evaluate_savings",
        return_value=mock_tp,
    ), patch(
        "app.services.two_pass_pipeline_service.TwoPassPipelineService.scan_video_for_action_windows",
        return_value=[],
    ):
        response = client.post("/api/v1/pipeline/two-pass/mock_vid")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["compute_reduction_percentage"] == 34.0


def test_api_benchmark_run_mocked():
    mock_report = BenchmarkComparisonReport(
        dataset_name="mock_vid",
        runs=[
            BenchmarkRunResult(
                video_id="mock_vid",
                processing_mode="full",
                total_frames=30,
                frames_processed=30,
                elapsed_time_seconds=1.0,
                effective_throughput_fps=30.0,
                speedup_ratio=1.0,
                accuracy=AccuracyMetrics(
                    mean_pose_confidence=0.9,
                    missing_keypoint_rate=0.0,
                    tracking_failure_rate=0.0,
                    contact_frame_delta=0,
                    contact_time_error_ms=0.0,
                ),
            )
        ],
        fastest_strategy="full",
        recommended_production_strategy="full",
    )
    with patch(
        "app.services.frame_extraction_service.FrameExtractionService._resolve_video_path",
        return_value=(MagicMock(), "mock_vid.mp4"),
    ), patch(
        "app.services.benchmark_service.BenchmarkService.run_benchmark_on_video",
        return_value=mock_report,
    ):
        response = client.post("/api/v1/benchmark/run/mock_vid")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_name"] == "mock_vid"
        assert len(data["runs"]) == 1


def test_api_pipeline_run_batting_stance_and_bat_3d():
    mock_pipeline_res = {
        "video_id": "mock_vid",
        "source_fps": 30.0,
        "processing_fps": 30.0,
        "processing_mode": "full",
        "total_frames": 10,
        "batter_handedness": "LHB",
        "bat_trajectory_3d": [
            {"frame_index": 0, "x": 0.2, "y": 1.1, "z": -0.4},
            {"frame_index": 1, "x": 0.4, "y": 1.0, "z": 0.1},
        ],
        "pose_3d_frames": [
            {
                "bat": {
                    "detected": True,
                    "handle": {"x": 0.1, "y": 0.9, "z": 0.0},
                    "barrel": {"x": 0.4, "y": 1.0, "z": 0.1},
                }
            }
        ],
    }
    with patch("app.api.routes.pipeline.run_pipeline", return_value=mock_pipeline_res) as mock_run:
        response = client.post(
            "/api/v1/pipeline/run/mock_vid",
            json={"batting_stance": "LHB", "processing_mode": "full"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "mock_vid"
        assert data["batter_handedness"] == "LHB"
        assert len(data["bat_trajectory_3d"]) == 2
        assert "bat" in data["pose_3d_frames"][0]
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["batting_stance"] == "LHB"

