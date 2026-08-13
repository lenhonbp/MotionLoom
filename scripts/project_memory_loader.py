"""Small import-safe bridge for the cross-platform analyzer."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).with_name("project-memory.py")
    spec = importlib.util.spec_from_file_location("motionloom_project_memory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Project Memory module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refresh_if_present(root: Path, context_path: Path, initialize: bool = False):
    module = _module()
    memory_path = (root / ".motionloom" / "project-memory.json").resolve()
    if not memory_path.exists():
        if not initialize:
            return None
        memory = module.base_memory(root, str(context_path))
        module.write_atomic(memory_path, memory)
        return {"status": "initialized", "memory_path": str(memory_path), "freshness": memory["freshness"]}
    memory = module.load_or_fail(memory_path)
    refreshed = module.refresh_memory(memory, root, str(context_path))
    module.write_atomic(memory_path, refreshed)
    return {"status": refreshed["freshness"]["status"], "memory_path": str(memory_path), "freshness": refreshed["freshness"]}
