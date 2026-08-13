# Agent consumer fixtures

This example set is a small, machine-readable map of how an Agent should consume MotionLoom. It is intentionally not a fake demo application and it does not claim user approval. Each case points to a repository artifact or a real runtime harness and states its evidence level.

Run the offline contract checks first:

```text
motionloom discovery check --root . --json
python3 tests/scripts/test_consumer_fixtures.py
```

For the browser-backed runtime cases, install the repository dependencies and run:

```text
npm run runtime:test
```

The real runtime harness emits deterministic scrub points at 0/50/100% for Rive, GSAP and Framer Motion. The Lottie and dotLottie cases are asset/package contracts; they must not be described as runtime-verified unless corresponding runtime evidence exists in the task bundle. The body-rig and continuity cases exercise structure and cross-scene semantics.
