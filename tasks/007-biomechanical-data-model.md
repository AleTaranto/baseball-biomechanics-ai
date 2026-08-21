# Task 007 ? Movement Data Model and Pose Sequence Validation

## Objective

Transform provider-specific pose outputs into a canonical, time-ordered movement representation and validate the resulting sequence before any downstream biomechanics processing.

## Scope

This task is intentionally limited to raw movement representation and quality validation. It does not implement smoothing, interpolation, biomechanical metrics, or swing segmentation.

### Required output model

`MovementRecording` is the canonical movement model for all downstream modules.

- `MovementRecording`
  - `recording_id`
  - `source_video_id`
  - `fps`
  - `duration` (milliseconds)
  - `frames`
  - `quality_summary`
- `FramePose`
  - `frame_index`
  - `timestamp` (milliseconds since recording start)
  - `joints`
- `JointObservation`
  - `joint_name`
  - `x`
  - `y`
  - `z` (optional)
  - `confidence` (optional)
  - `visibility` (optional)

Raw provider outputs remain technical artifacts and must not be treated as the canonical contract for downstream movement analysis. The adapter boundary is responsible for converting provider-native units into the canonical millisecond-based movement contract.

### Validation requirements

The validator must flag at least:

- missing frames;
- non-ordered timestamps;
- missing joints;
- low confidence or visibility values;
- frames without pose detection;
- invalid coordinates;
- temporal discontinuities.

The system must report these issues but not attempt auto-correction.

### Quality summary

The movement model must produce a `PoseSequenceQuality` object containing at least:

- total frames;
- frames with pose;
- frames without pose;
- missing joint counts;
- low-confidence joint counts;
- temporal continuity status.

## Implementation notes

- the internal model must remain provider-agnostic;
- conversion from the pose provider format should use a dedicated mapper/adapter;
- the sequence remains serializable as JSON for inspection and future processing;
- output should be stored alongside pose-estimation data for later analysis.

## Acceptance criteria

The task is complete when a sample video can be processed as:

video -> frames -> pose estimation -> raw keypoints -> MovementRecording -> quality summary

and the resulting record can be inspected as structured data with validation issues exposed rather than silently corrected.
