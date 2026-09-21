# Task 008 ? Kinematic Calculations V1

## Objective

Convert a canonical `MovementRecording` into a derived `KinematicRecording` that exposes geometric and temporal quantities derived directly from observed motion. This task is limited to calculation and validation: it does not interpret swing quality or infer biomechanics.

## Scope

The module must consume only the canonical movement model and not depend on raw provider output.

### Required calculations

1. Joint angles
   - left elbow angle
   - right elbow angle
   - left knee angle
   - right knee angle
   - all values in degrees

2. Segment vectors
   - left upper arm
   - right upper arm
   - left forearm
   - right forearm
   - left thigh
   - right thigh
   - left shank
   - right shank
   - shoulder line vector
   - hip line vector

3. Linear velocity
   - left wrist
   - right wrist
   - left shoulder
   - right shoulder
   - left hip
   - right hip
   - computed using actual timestamp deltas
   - expressed as `normalized_units_per_second`

### Validity requirements

Every derived metric must carry validity metadata:

- value or null
- valid boolean
- reason when invalid
- input quality score when available

Invalid inputs must be reported explicitly without silence, smoothing, or interpolation.

## Output contract

The canonical output is a `KinematicRecording` containing ordered frame-level kinematic data derived from the movement sequence.

- `recording_id`
- `source_video_id`
- `source_recording_id`
- `fps`
- `duration`
- `frames`

Each frame contains:

- `frame_index`
- `timestamp`
- `joint_angles`
- `segment_vectors`
- `linear_velocities`

## Edge cases to handle explicitly

- first frame without a previous frame
- missing frames and missing joints
- zero or negative time delta
- invalid timestamps
- invalid coordinates
- low-confidence inputs

## Persistence

Kinematic output must be saved separately from the movement JSON. The raw movement record remains the observation layer and must not be overwritten by the kinematic analysis.

## Acceptance criteria

- A `MovementRecording` can be converted to a `KinematicRecording`.
- Joint angles are calculated for elbows and knees.
- Segment vectors are available.
- Linear velocities use real timestamp differences.
- Invalid metrics are explicit and never silently produced.
- At least one real swing is processed end-to-end.
- Tests and validation pass.

## Notes

This task intentionally excludes interpretation, scoring, injury risk estimation, phase detection, coaching recommendations, and any smoothing or automatic correction.
