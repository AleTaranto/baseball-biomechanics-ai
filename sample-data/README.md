# Sample data

This directory contains test-data metadata, uploaded media, and extracted processing outputs related to baseball swing analysis. Heavy video files should not be versioned directly unless there is a strong reason to do so.

## Upload directory

The application stores uploaded videos in `sample-data/uploads/` by default. This folder is intentionally excluded from version control to keep the repository lightweight while still supporting local ingestion tests and development.

## Extracted frame directory

Frame extraction writes a dedicated output structure under `sample-data/frames/<video_id>/`.

Each video gets:

- `sample-data/frames/<video_id>/frame_000000.png` ... `frame_NNNNNN.png` — ordered frame images;
- `sample-data/frames/<video_id>/manifest.json` — metadata for all extracted frames.

The manifest includes:

- the source video id and path;
- the frame rate when it can be detected;
- the total number of extracted frames;
- a per-frame entry with `frame_index`, `timestamp_ms`, `file_name`, `relative_path`, `width`, and `height`.

This structure keeps the raw video source, extracted intermediary frames, and downstream metadata easy to inspect without coupling the data model to an API endpoint.

## Future storage strategies

- Git LFS for selected small reference videos;
- object storage for larger media assets;
- external datasets with explicit provenance and licensing review.
