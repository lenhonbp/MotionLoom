# Canonical live Dev Lab sprite fixture

This fixture is a small, hash-bindable sprite-sequence runtime for exercising the Dev Lab live path from a clean checkout. It deliberately contains two review-required actions, `idle` and `reverse`, so the Action Library coverage gate can be observed moving from `1/2` to `2/2`.

The PNG files are deterministic repository fixtures. They are suitable for runtime-control and provenance-contract testing; they are **not** a claim about production art quality, identity fidelity, licensing, authorship or user approval.

## Run the live binding check

From the repository root:

```bash
python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path

root = Path(".").resolve()
sys.path.insert(0, str(root / "scripts"))
path = root / "scripts/review-hook.py"
spec = importlib.util.spec_from_file_location("motionloom_review_hook", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
bundle = module.runtime_bundle(root / "examples/agent-consumer/devlab-live-sprite")
assert bundle and bundle["mode"] == "sprite-sequence"
assert bundle["animations"] == ["idle", "reverse"]
print(bundle["bundle_sha256"])
PY
```

To use the fixture in an actual review task, copy it into a rendered scene directory as `devlab-runtime.json` and run `motionloom review-hook prepare --task-dir <task-dir> --lab-url <dev-lab-url>`. Open the exact emitted candidate URL, inspect both actions, exercise play/pause/restart/seek/step/speed/loop, and obtain explicit user approval before any PR workflow.
