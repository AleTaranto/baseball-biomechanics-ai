# Task 004 — Frame Extraction

## Objective

Add a dedicated frame extraction stage for videos already ingested by the platform, so the system can produce ordered frame snapshots with timestamps and stable metadata for downstream analysis.

## Context

The project is deliberately moving in small milestones. After ingestion, the next stage is to turn each validated video into a sequence of time-ordered frames without mixing business logic into the API layer. This task is limited to extraction and metadata generation; pose estimation and biomechanical interpretation remain out of scope.

## Scope

- use a video-decoding library to read ingested file assets;
- keep extraction logic in a dedicated service layer rather than inside endpoints;
- preserve temporal ordering of frames across the full clip;
- assign each frame a deterministic index and timestamp in milliseconds;
- output a saved frame image and manifest metadata for each extracted video;
- handle corrupt or unreadable videos with clear validation errors;
- add automated tests for the extraction flow and edge cases;
- document the output structure and where the files are stored;
- keep compatibility with the existing upload workflow and metadata conventions.

## Out of Scope

- pose estimation;
- joint angle reconstruction;
- biomechanics scoring;
- database-backed frame persistence;
- asynchronous scheduling or background workers.

## Technical Requirements

- extract frames from videos already stored under `sample-data/uploads/`;
- use OpenCV (`cv2`) for frame reading and writing;
- write extracted images under `sample-data/frames/<video_id>/`;
- keep file names ordered using zero-padded index format, e.g. `frame_000000.png`;
- persist a JSON manifest for each video at `sample-data/frames/<video_id>/manifest.json`;
- expose the extraction logic via a service object and a thin API route;
- reject unreadable or empty video assets with `ValueError` and a 400 response;
- keep the extracted metadata compatible with future downstream stages.

## Acceptance Criteria

- a valid uploaded video can be processed through the frame extraction service;
- extracted frames are stored in time order and are associated with frame index + timestamp metadata;
- a manifest JSON exists for each extracted video;
- invalid or corrupt video input fails with a clear error;
- all project checks (pytest, Ruff, and mypy) pass.

## Tests Required

- a valid video yields a deterministic, ordered frame list;
- frame metadata includes index and timestamp values in ascending order;
- corrupt or unreadable video input raises a clear validation error;
- the API route can trigger extraction and return the manifest payload.

## Documentation Updates

- document the frame storage structure in `sample-data/README.md`;
- describe the extracted-frame manifest and its fields in the project docs;
- include a brief mention of the current processing milestone in `README.md`.

## Dependencies

- video ingestion task completed and stored in `sample-data/uploads/`;
- OpenCV available in the project environment;
- a stable file naming convention for extracted frames and metadata.

## Definition of Done

The task is complete when extracted frames are generated from valid uploaded videos, metadata is traceable and ordered, corrupted inputs fail predictably, and the repository remains green under automated validation.
