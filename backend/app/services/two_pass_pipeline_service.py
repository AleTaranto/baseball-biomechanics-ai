from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from app.schemas.two_pass import ActionWindow, TwoPassConfig, TwoPassResult


class TwoPassPipelineService:
    """Implements two-pass processing architecture (Strategy F):

    Pass 1: Cheap downsampled scan to locate candidate action windows.
    Pass 2: High-framerate deep kinematic analysis restricted exclusively to active windows.
    """

    @staticmethod
    def compute_frame_difference_energy(img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute normalized global motion energy between two grayscale frames."""
        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        diff = cv2.absdiff(g1, g2)
        # Normalized mean difference [0.0, 1.0]
        return float(np.mean(diff) / 255.0)

    @classmethod
    def scan_video_for_action_windows(
        cls,
        frames_dir: Path,
        fps: float = 30.0,
        config: TwoPassConfig | None = None,
        motion_threshold: float = 0.015,
    ) -> list[ActionWindow]:
        """Pass 1: Rapid downsampled scan across extracted frames

        to detect candidate action windows.
        """
        cfg = config or TwoPassConfig(scan_sampling_interval=4, window_padding_seconds=0.3)
        frame_files = sorted(
            list(frames_dir.glob("*.png")) + list(frames_dir.glob("*.jpg")),
            key=lambda p: int("".join(filter(str.isdigit, p.stem)) or "0"),
        )
        total_frames = len(frame_files)
        if total_frames < 2:
            return []

        sampled_indices = list(range(0, total_frames, cfg.scan_sampling_interval))
        if sampled_indices[-1] != total_frames - 1:
            sampled_indices.append(total_frames - 1)

        energies: list[tuple[int, float]] = []
        prev_img: np.ndarray | None = None

        for idx in sampled_indices:
            curr_img = cv2.imread(str(frame_files[idx]), cv2.IMREAD_COLOR)
            if curr_img is None:
                continue
            # Downscale for ultra-fast motion estimation
            h, w = curr_img.shape[:2]
            small = cv2.resize(curr_img, (min(160, w), min(120, h)), interpolation=cv2.INTER_AREA)
            if prev_img is not None:
                energy = cls.compute_frame_difference_energy(prev_img, small)
                energies.append((idx, energy))
            prev_img = small

        # Find continuous sequences of frames exceeding threshold
        active_clusters: list[list[int]] = []
        current_cluster: list[int] = []

        for frame_idx, energy in energies:
            if energy >= motion_threshold:
                current_cluster.append(frame_idx)
            else:
                if current_cluster:
                    active_clusters.append(current_cluster)
                    current_cluster = []
        if current_cluster:
            active_clusters.append(current_cluster)

        padding_frames = int(round(cfg.window_padding_seconds * fps))
        raw_windows: list[tuple[int, int]] = []

        for cluster in active_clusters:
            start_f = max(0, min(cluster) - cfg.scan_sampling_interval - padding_frames)
            end_f = min(total_frames - 1, max(cluster) + padding_frames)
            raw_windows.append((start_f, end_f))

        # Merge overlapping or touching windows
        merged: list[tuple[int, int]] = []
        for start_f, end_f in sorted(raw_windows, key=lambda w: w[0]):
            if not merged:
                merged.append((start_f, end_f))
            else:
                prev_s, prev_e = merged[-1]
                if start_f <= prev_e + 2:
                    merged[-1] = (prev_s, max(prev_e, end_f))
                else:
                    merged.append((start_f, end_f))

        action_windows: list[ActionWindow] = []
        for s, e in merged:
            action_windows.append(
                ActionWindow(
                    start_frame=s,
                    end_frame=e,
                    start_time_seconds=s / fps,
                    end_time_seconds=e / fps,
                    action_type="swing",
                )
            )

        return action_windows

    @classmethod
    def evaluate_savings(
        cls,
        video_id: str,
        total_frames: int,
        action_windows: list[ActionWindow],
        config: TwoPassConfig | None = None,
    ) -> TwoPassResult:
        """Calculate compute reduction of two-pass processing vs naive full-rate evaluation."""
        cfg = config or TwoPassConfig(scan_sampling_interval=4, window_padding_seconds=0.3)
        pass1_frames = int(math.ceil(total_frames / cfg.scan_sampling_interval))

        pass2_unique_frames: set[int] = set()
        for w in action_windows:
            for f in range(w.start_frame, min(total_frames, w.end_frame + 1)):
                pass2_unique_frames.add(f)

        pass2_frames = len(pass2_unique_frames)
        total_processed = pass1_frames + pass2_frames

        if total_frames > 0:
            reduction = max(
                0.0,
                100.0 * (1.0 - (total_processed / float(total_frames))),
            )
        else:
            reduction = 0.0

        return TwoPassResult(
            video_id=video_id,
            total_video_frames=total_frames,
            pass1_scanned_frames=pass1_frames,
            pass2_analyzed_frames=pass2_frames,
            total_processed_frames=total_processed,
            compute_reduction_percentage=reduction,
            action_windows=action_windows,
        )
