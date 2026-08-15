# Rive package gate — real package handoff

This directory intentionally contains **no fake production `.riv` package**. Put a concrete package here only after it exists, then create a manifest that binds its bytes, provenance and runtime proof.

```text
hero.riv
hero-provenance.json
hero-runtime-evidence.json
hero-rive-package.json
```

The manifest must use `runtime.adapter_id: "motionloom.rive-runtime"`, list declared state-machine/input/event controls, and preserve `review_required: true`. In strict mode, runtime evidence must bind `source_sha256` to the exact `hero.riv` bytes and report a passing ready Rive framework capture.

```bash
npx --yes motionloom rive-gate validate \
  --input examples/agent-consumer/rive-package-gate/hero-rive-package.json \
  --root . --strict --json
```

> A passing gate means only that the package is ready for runtime testing and human review. It never creates artist authority, production eligibility, production approval, a Git push, or a pull request.
