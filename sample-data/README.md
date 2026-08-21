# Sample data

This directory contains test-data metadata and future fixtures related to baseball swing analysis. Heavy video files should not be versioned directly unless there is a strong reason to do so.

## Upload directory

The application stores uploaded videos in `sample-data/uploads/` by default. This folder is intentionally excluded from version control to keep the repository lightweight while still supporting local ingestion tests and development.

## Future storage strategies

- Git LFS for selected small reference videos;
- object storage for larger media assets;
- external datasets with explicit provenance and licensing review.
