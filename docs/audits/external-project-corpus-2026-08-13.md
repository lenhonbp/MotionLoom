# External Project Corpus Evidence — 2026-08-13

## Purpose

This is a labeled analyzer evaluation, not a claim that MotionLoom has been validated across the entire animation ecosystem. The runner reads explicit checkouts only; it does not install dependencies, execute external project code, or treat an absent checkout as a pass.

## Reproducibility

The evaluation used `python3 scripts/eval-projects.py` with the default bounded scan policy: at most 2,500 files, 25,000,000 bytes and 10 seconds per project. The first-party repository was evaluated from the local MotionLoom checkout. External checkouts were placed under `external/` in a temporary workspace and pinned to the following observed commits.

| Case | Source | Observed revision | Result | Signals checked |
|---|---|---|---|---|
| MotionLoom | [lenhonbp/MotionLoom](https://github.com/lenhonbp/MotionLoom) | local checkout | PASS | `name=motionloom` |
| Motion One | [motiondivision/motion](https://github.com/motiondivision/motion) | `adaf7a4e5368d704ea350669f6ac674fb26ff270` | PASS | `name=motion-one`, `framework=motion` |
| GSAP | [greensock/GSAP](https://github.com/greensock/GSAP) | `13e2b790546426a1a2e0e9b409f3f8dc6d6611f2` | PASS | `framework=gsap` |
| Rive React | [rive-app/rive-react](https://github.com/rive-app/rive-react) | `c05ec1842324a4a61d01f8e49dfd2ac2c37ae72c` | PASS | `name=rive-react`, `framework=rive` |

The final report was `status=pass`, with 3/3 required external projects available and 4/4 total cases passing. All four scans reported `scan_truncated=false` under the stated budgets.

## Interpretation

The package-identity precedence change is material. Motion One is a monorepo whose root workspace contains GSAP tooling; a dependency-only detector labeled it GSAP. Rive React similarly contains React dependencies but should expose a Rive runtime signal. MotionLoom now prefers an exact package identity (`motion`, `motion-one`, `framer-motion`, Rive packages) before generic dependency fallback, while retaining the bounded scan metadata.

This evidence supports a **small, reproducible analyzer corpus signal**. It does not prove animation quality, runtime correctness, visual fidelity, accessibility, licensing compliance, or first-pass acceptance. Those remain separate gates requiring runtime evidence, Dev Lab review and explicit user confirmation.

When external checkouts are not supplied, the same command intentionally reports `insufficient_evidence`; CI uses `--allow-insufficient` for visibility without converting missing product evidence into a green product claim.
