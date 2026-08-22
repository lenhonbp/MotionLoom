"""Fetch the explicitly requested external analyzer corpus without installing or executing it."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests/evals/project-corpus.json"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result.stdout.strip()


def safe_destination(workspace: Path, relative: str) -> Path:
    destination = (workspace / relative).resolve()
    if workspace.resolve() not in destination.parents:
        raise ValueError(f"manifest local_path escapes workspace: {relative}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--workspace", required=True, help="Directory that will contain external checkouts")
    parser.add_argument("--project", action="append", default=[], help="Manifest project id; repeatable")
    parser.add_argument("--all", action="store_true", help="Fetch every external project in the manifest")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--refresh", action="store_true", help="Remove and re-fetch existing selected checkouts")
    args = parser.parse_args()
    if not args.all and not args.project:
        parser.error("choose --all or at least one --project")
    if args.depth < 1:
        parser.error("--depth must be positive")

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = [case for case in manifest.get("projects", []) if case.get("external") is True]
    selected = set(case["id"] for case in cases) if args.all else set(args.project)
    known = {case["id"] for case in cases}
    unknown = sorted(selected - known)
    if unknown:
        raise ValueError(f"unknown external project id(s): {', '.join(unknown)}")

    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    fetched: list[dict[str, str]] = []
    for case in cases:
        if case["id"] not in selected:
            continue
        destination = safe_destination(workspace, str(case["local_path"]))
        if destination.exists() or destination.is_symlink():
            if not args.refresh:
                raise RuntimeError(f"checkout already exists: {destination}; pass --refresh to replace it")
            if destination.is_symlink() or not destination.is_dir():
                raise RuntimeError(f"refusing to remove non-directory checkout path: {destination}")
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = str(case["source"])
        run(["git", "clone", "--depth", str(args.depth), source, str(destination)])
        commit = run(["git", "rev-parse", "HEAD"], cwd=destination)
        fetched.append({"id": case["id"], "source": source, "path": str(destination), "commit": commit})

    record = {
        "schema_version": "1.0",
        "manifest": str(manifest_path),
        "fetched_at": now(),
        "policy": "clone-only; no install, build, test or external code execution",
        "projects": fetched,
    }
    record_path = workspace / ".motionloom-corpus-fetch.json"
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "workspace": str(workspace), "projects": fetched, "record": str(record_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
