# Task Inventory — Baseball Biomechanics AI

All project milestones and features are tracked and executed as discrete tasks in this directory.

| Task ID | Title | Description | Status |
|---|---|---|---|
| [001](001-project-bootstrap.md) | Project Bootstrap & Foundation | Repository setup, pyproject.toml, directory structure, and test suite. | Completed |
| [002](002-video-ingestion.md) | Video Ingestion Service | Upload handling, extension validation, and raw payload storage. | Completed |
| [003](003-video-validation.md) | Video Validation & Quality Gates | Framerate (120 FPS) and resolution validation without lossy transcoding. | Completed |
| [004](004-frame-extraction.md) | Frame Extraction Service | High-throughput OpenCV decoding and frame manifest generation. | Completed |
| [005](005-pose-estimation.md) | Pose Estimation Service | MediaPipe BlazePose landmark extraction and debug overlay generator. | Completed |
| [006](006-swing-segmentation.md) | Swing Window Segmentation | Wrist speed kinematic energy filtering and temporal swing boundary detection. | Completed |
| [007](007-biomechanical-data-model.md) | Biomechanical Data Model | Canonical `MovementRecording` schema, validation rules, and quality scoring. | Completed |
| [008](008-kinematic-calculations-v1.md) | Kinematic Calculations (v1) | Joint angles, linear velocities, and temporal derivative estimation. | Completed |
| [009](009-batting-biomechanical-metrics.md) | Batting Biomechanical Metrics | X-Factor hip-shoulder separation, torso tilt, head drift, and hand path. | Completed |
| [010](010-bat-tracking.md) | Standalone Bat Tracker | Canny/Hough shaft detection, sweet spot tracking, and barrel attack angle. | Completed |
| [011](011-contact-detection.md) | Multi-Signal Contact Detector | Consensus timing across bat speed, hand deceleration, and segmentation priors. | Completed |
| [012](012-generic-biomechanics-engine.md) | Generic Biomechanics Engine | Reusable mathematical and kinematic primitives agnostic to sport action. | Completed |
| [013](013-advanced-biomechanical-visualization.md) | Advanced Visual Overlays | Bat trajectory trails, HUD phase badges, live X-factor, and contact flash banners. | Completed |
| [014](014-two-pass-performance-pipeline.md) | Two-Pass Performance Pipeline | Fast downsampled coarse scan and deep pose estimation pruning on active windows. | Completed |
| [015](015-benchmark-and-accuracy-suite.md) | Benchmark & Accuracy Suite | Throughput profiler, FPS speedup multipliers, and kinematic error benchmarking. | Completed |
| [016](016-pitching-biomechanics-analyzer.md) | Pitching Biomechanics Analyzer | Pitch delivery milestones, temporal phases, stride length, and arm slot angle. | Completed |
| [017](017-pitching-visual-overlays.md) | Pitching Visual Overlays | Stride length baseline indicators, arm slot vector rays, and release event HUD. | Completed |
| [018](018-api-endpoints-biomechanics-pipeline.md) | Production REST API Endpoints | FastAPI routes exposing batting, pitching, pipelines, and benchmark comparison. | Completed |
| [019](019-interactive-web-visualizer-dashboard.md) | Interactive Web Visualizer Dashboard | Responsive HTML5/Tailwind/Chart.js frontend for video playback, frame scrubbing, overlay toggles, and metrics. | Completed |
