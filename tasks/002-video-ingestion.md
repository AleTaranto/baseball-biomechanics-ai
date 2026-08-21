# Task 002 — Video Ingestion

## Objective

Add the first ingestion workflow for local video files so the platform can accept a valid video upload, validate it, persist it under the sample-data storage area, and record metadata for downstream processing.

## Context

The project is intentionally moving in small milestones. The ingestion layer is the first operational boundary after the repository bootstrap. It must be simple, explicit, and testable without introducing speculative features from later stages like pose estimation or biomechanics analysis.

## Scope

- implement a FastAPI upload endpoint;
- validate filename and MIME/type constraints for supported video formats;
- enforce a maximum upload size;
- store uploaded files under `sample-data/uploads/`;
- write a JSON metadata file for each upload;
- expose a minimal response with metadata required for future processing.

## Out of Scope

- pose estimation;
- biomechanics interpretation;
- video transcoding;
- asynchronous background processing;
- database-backed persistence.

## Technical Requirements

- FastAPI upload endpoint using multipart form data;
- support for `.mp4`, `.mov`, `.avi`, `.m4v`, `.wmv`, and `.webm`;
- reject empty or unsupported files with a clear 400 response;
- save file bytes locally to the repository-managed upload directory;
- keep app configuration in `Settings` using environment variables;
- use type hints and tests for the upload flow.

## Acceptance Criteria

- a valid file upload returns HTTP 201;
- the uploaded file is stored under `sample-data/uploads/`;
- metadata JSON is created for the file;
- invalid file types are rejected;
- project validation passes via Ruff, mypy, and pytest.

## Tests Required

- valid MP4 upload succeeds;
- invalid extension returns a 400 response;
- upload metadata contains expected path and content information.

## Documentation Updates

- update repository README to mention the ingestion flow and upload directory;
- update `sample-data/README.md` to document storage expectations.

## Dependencies

- project bootstrap task completed;
- `python-multipart` installed for FastAPI form-data uploads.

## Definition of Done

The task is complete when valid video files can be uploaded through the API, invalid input is rejected cleanly, metadata is persisted, and the project remains green under automated validation.
