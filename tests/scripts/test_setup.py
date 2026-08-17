"""Regression tests for the no-network MotionLoom onboarding wizard."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node") or "node"


def run_cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [NODE, str(ROOT / "bin/motionloom.mjs"), *args, "--project-root", str(project), "--motionloom-root", str(ROOT), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_cli_from_project(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Exercise the installed-CLI default: the caller cwd is the project root."""
    return subprocess.run(
        [NODE, str(ROOT / "bin/motionloom.mjs"), *args, "--motionloom-root", str(ROOT), "--json"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        (project / "package.json").write_text(
            json.dumps({"name": "setup-fixture", "private": True}), encoding="utf-8"
        )

        caller_dry = run_cli_from_project(project, "init", "--dry-run")
        try:
            caller_payload = json.loads(caller_dry.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"caller-root init did not emit JSON: {exc}")
            caller_payload = {}
        if caller_dry.returncode != 0 or Path(caller_payload.get("project_root", "")) != project.resolve():
            errors.append(f"CLI should preserve the caller working directory: {caller_payload}")
        if any((project / path).exists() for path in ("AGENTS.md", "project-context.json", ".motionloom")):
            errors.append("caller-root dry-run changed the project")

        dry = run_cli(project, "setup", "--dry-run")
        try:
            dry_payload = json.loads(dry.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"setup dry-run did not emit JSON: {exc}")
            dry_payload = {}
        if dry.returncode != 0 or dry_payload.get("status") != "planned":
            errors.append(f"setup dry-run should be planned: {dry_payload}")
        if any((project / path).exists() for path in ("AGENTS.md", "project-context.json", ".motionloom")):
            errors.append("setup dry-run changed the project")

        init_dry = run_cli(project, "init", "--dry-run")
        try:
            init_payload = json.loads(init_dry.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"init dry-run did not emit JSON: {exc}")
            init_payload = {}
        if init_dry.returncode != 0 or init_payload.get("status") != "planned" or init_payload.get("onboarding") != "quick_start":
            errors.append(f"init should expose the quick-start contract: {init_payload}")

        package = json.loads((project / "package.json").read_text(encoding="utf-8"))
        package["devDependencies"] = {"motionloom": "2.2.0"}
        (project / "package.json").write_text(json.dumps(package), encoding="utf-8")
        setup = run_cli(project, "setup")
        try:
            setup_payload = json.loads(setup.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"setup did not emit JSON: {exc}")
            setup_payload = {}
        if setup.returncode != 0 or setup_payload.get("status") != "ready":
            errors.append(f"setup should reach ready: {setup_payload}")
        router = (project / "AGENTS.md").read_text(encoding="utf-8") if (project / "AGENTS.md").exists() else ""
        if router.count("MOTIONLOOM:START") != 1 or router.count("MOTIONLOOM:END") != 1:
            errors.append("setup did not create one managed Agent router block")
        if not (project / "project-context.json").is_file() or not (project / ".motionloom/project-memory.json").is_file():
            errors.append("setup did not bootstrap project context and durable memory")

        repeat = run_cli(project, "setup")
        repeat_payload = json.loads(repeat.stdout)
        if repeat.returncode != 0 or repeat_payload.get("status") != "ready":
            errors.append("setup is not idempotent on a ready project")
        router_after = (project / "AGENTS.md").read_text(encoding="utf-8")
        if router_after.count("MOTIONLOOM:START") != 1:
            errors.append("repeated setup duplicated the Agent router block")

        status = run_cli(project, "status")
        status_payload = json.loads(status.stdout)
        if status.returncode != 0 or status_payload.get("status") != "ready":
            errors.append(f"status should report ready: {status_payload}")
        if status_payload.get("quick_start", {}).get("gates_active") is not False:
            errors.append("status should confirm that setup does not activate animation gates")

        (project / "AGENTS.md").unlink()
        repair = run_cli(project, "repair", "--skip-install", "--skip-memory", "--yes")
        repair_payload = json.loads(repair.stdout)
        if repair.returncode != 0 or repair_payload.get("status") != "ready":
            errors.append(f"repair should restore a ready project: {repair_payload}")
        repaired_router = (project / "AGENTS.md").read_text(encoding="utf-8") if (project / "AGENTS.md").exists() else ""
        if repaired_router.count("MOTIONLOOM:START") != 1 or repaired_router.count("MOTIONLOOM:END") != 1:
            errors.append("repair did not restore one managed Agent router block")

    if errors:
        print("setup onboarding tests: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("setup onboarding tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
