# Engineering principles

This document defines the rules that future coding agents should follow when changing the codebase.

## Core principles

- Work on one task at a time.
- Read the relevant specification before making changes.
- Do not modify unrelated modules.
- Add or update tests when changing behavior.
- Run the relevant validation commands after code changes.
- Keep commits small and atomic.
- Document important decisions and trade-offs.
- Avoid breaking changes without updating the relevant specification.
- Do not implement speculative features before a real use case exists.

## Quality bar

- keep business logic out of API route handlers;
- separate API, domain logic, services, and infrastructure;
- prefer a small number of testable components over monolithic files;
- keep type hints complete and accurate;
- prefer maintainable, explicit designs over clever shortcuts.
