# Architecture Decision Log

## ADR-001 ? Python as the primary language

- Date: 2026-08-21
- Status: Accepted
- Context: The project needs a backend oriented toward scientific workflows, data processing, and API exposure.
- Decision: Use Python as the main language for backend development and future scientific pipeline work.
- Consequences: Better ecosystem support, simpler prototype iteration, and easier experimentation with data processing and ML tooling.
- Alternatives considered: JavaScript-only backend, Java-only stack, and a mixed-language approach. The Python-based stack is simpler and aligns with the domain.

## ADR-002 ? FastAPI as the API framework

- Date: 2026-08-21
- Status: Accepted
- Context: The service requires a fast and modern API with Python type safety and testability.
- Decision: Use FastAPI as the application framework.
- Consequences: Strong validation, concise routing, and ease of extension for future APIs.
- Alternatives considered: Flask and Django. FastAPI provides better async support and type validation for a growing science platform.

## ADR-003 ? Modular architecture

- Date: 2026-08-21
- Status: Accepted
- Context: The project will evolve toward multiple distinct subsystems and must stay maintainable.
- Decision: Structure the codebase into separate API, domain, services, infrastructure, and knowledge layers.
- Consequences: Easier scaling, clearer ownership, and fewer circular dependencies.
- Alternatives considered: a single monolithic package. The modular design reduces unnecessary coupling.

## ADR-004 ? Separate computer vision and biomechanics engine

- Date: 2026-08-21
- Status: Accepted
- Context: Media processing and interpretation are distinct concerns that need independent refinement.
- Decision: Keep computer vision, motion reconstruction, and biomechanics interpretation separated by design.
- Consequences: Each subsystem can evolve with different dependencies and validation strategies.
- Alternatives considered: tightly coupling pose estimation and interpretation into one code path. This would increase maintenance complexity.

## ADR-005 ? Markerless approach as default

- Date: 2026-08-21
- Status: Accepted
- Context: Markerless tracking is more scalable for future athlete deployments and reduces setup friction.
- Decision: Prefer a markerless motion-analysis pipeline as the default approach.
- Consequences: Lower setup burden, broader use cases, and a clearer path to video-based analysis.
- Alternatives considered: marker-based systems. These are more intrusive and harder to deploy at scale.

## ADR-006 ? Incremental delivery with atomic tasks

- Date: 2026-08-21
- Status: Accepted
- Context: The project spans research, infrastructure, and product work and needs a stable base at every stage.
- Decision: Implement the system in small, testable tasks with one milestone active at a time.
- Consequences: Lower risk, clearer reviews, and more predictable progress.
- Alternatives considered: large multi-feature changes in a single PR. This generates instability and reduces traceability.

## ADR-007 ? No medical diagnosis by the system

- Date: 2026-08-21
- Status: Accepted
- Context: Sports biomechanics can influence injury prevention conversations and coaching interpretations.
- Decision: The platform will never produce medical diagnoses or direct treatment guidance.
- Consequences: Clear product boundaries and safer downstream use from coaches and practitioners.
- Alternatives considered: direct clinical diagnosis features. These would exceed the project scope and require strict clinical review.
