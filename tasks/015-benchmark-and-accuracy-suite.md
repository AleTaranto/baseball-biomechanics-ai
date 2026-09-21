# Task 015 — Benchmark Dataset & Accuracy Evaluation Suite

## Objective

Create a systematic benchmarking and accuracy measurement suite (`BenchmarkService`) to profile processing throughput (FPS), compute speedups, and quantify kinematic error metrics (missing keypoint rate, tracking failures, and contact frame deviations) across pipeline optimization strategies (`full`, `half_rate`, `two_pass`).

## Context

According to Section 16 & 17 of `plan_extended.txt`:
"16. Benchmark dataset: Every performance change must be tested against the same benchmark.
17. Accuracy tests: Measure keypoint positional error, tracking failure rate, missing-keypoint rate, swing detection error, contact-frame error, phase detection error, trajectory error."

## Scope

- Define canonical schemas in `backend/app/schemas/benchmark.py`:
  - `AccuracyMetrics`: landmark confidence, missing keypoint fraction, tracking failure rate, contact frame delta ($\Delta\text{frame}$ and $\Delta t$ in ms).
  - `BenchmarkRunResult`: mode, total vs. processed frames, elapsed duration, throughput FPS, speedup ratio against baseline full-rate.
  - `BenchmarkComparisonReport`: multi-strategy comparison across standardized runs, identifying fastest and recommended production modes.
- Implement `BenchmarkService` in `backend/app/services/benchmark_service.py`:
  - `evaluate_accuracy`: automated quality scoring against movement recordings and ground truth keyframes.
  - `run_benchmark_on_video`: multi-run executor recording exact elapsed time, computing speedup multipliers and persisting JSON reports under `sample-data/benchmark/`.
- Unit tests in `backend/tests/unit/test_benchmark_service.py`.

## Acceptance Criteria

- [x] Schemas defined in `backend/app/schemas/benchmark.py`.
- [x] Accuracy evaluator computing keypoint missing rates and contact time errors.
- [x] Strategy comparative runner computing speedup ratios.
- [x] Persists reports in `sample-data/benchmark/`.
- [x] Unit test suite passing (74/74 total tests).
