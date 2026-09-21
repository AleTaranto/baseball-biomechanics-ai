# Task 012 — Generic Biomechanics Engine

## Objective

Create an action-agnostic computational engine (`BiomechanicsEngine`) that standardizes reusable geometric and physical primitives (`JointAngle`, `SegmentAngle`, `VelocityVector`, `AccelerationVector`, `AngularVelocity`, `Trajectory`, `EventTiming`, `PhaseDuration`), decoupling core kinematics from sport-specific logic (batting vs. pitching).

## Context

According to Section 12 of `plan_extended.txt`:
"Create reusable primitives: JointAngle, Distance, Velocity, Acceleration, AngularVelocity, Trajectory, RelativePosition, BodyOrientation, SegmentAngle, EventTiming, PhaseDuration. These primitives should not know whether the movement is batting or pitching."

## Scope

- Define canonical Pydantic schemas in `backend/app/schemas/biomechanics_engine.py`:
  - `JointAngle`: 3-point vertex angle with confidence and validity.
  - `SegmentAngle`: orientation of implement or anatomical limb against horizontal/vertical axes.
  - `DistanceMeasurement`: Euclidean 2D/3D and component-wise deltas ($dx, dy, dz$).
  - `VelocityVector`: linear speed magnitude and vector components ($vx, vy, vz$).
  - `AccelerationVector`: linear acceleration magnitude and vector components ($ax, ay, az$).
  - `AngularVelocity`: rotational speed in deg/s with directional flag and 360-degree boundary wrap handling.
  - `Trajectory` & `TrajectoryPoint`: cumulative spatial sequence with cumulative arc length and peak speed extraction.
  - `EventTiming`: temporal positioning and relative offset ($\Delta t$ in ms) against an anchor milestone (such as contact/release).
  - `PhaseDuration`: duration and frame counts of athletic phases.
- Implement `BiomechanicsEngine` in `backend/app/services/biomechanics_engine.py`.
- Refactor `BattingMetricsService` to consume the engine primitives for angular and distance calculations.
- Implement comprehensive unit tests in `backend/tests/unit/test_biomechanics_engine.py`.

## Acceptance Criteria

- [x] Schemas defined in `backend/app/schemas/biomechanics_engine.py`.
- [x] Agnostic calculation methods implemented in `backend/app/services/biomechanics_engine.py`.
- [x] 360-degree circular boundary wrap handled accurately in angular velocity.
- [x] Batting metrics service refactored to delegate core mathematics to `BiomechanicsEngine`.
- [x] Unit test suite covering all primitives passing with 100% success.
