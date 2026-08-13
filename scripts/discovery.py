#!/usr/bin/env python3
"""Validate and expose MotionLoom's cross-agent discovery contract.

The command is deliberately offline and read-only. It verifies that every
Agent-facing surface points back to the canonical root SKILL.md, that install
recipes name a deterministic verification command, and that the package can be
discovered from a clean npm/Git/local checkout without inferring approval.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INVALID = 11


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_package(root: Path) -> dict[str, Any]:
    package = load_json(root / "package.json")
    return package if isinstance(package, dict) else {}


def git_remote(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value or None


def source_identity(root: Path) -> dict[str, Any]:
    package = read_package(root)
    return {
        "name": package.get("name"),
        "version": package.get("version"),
        "root": str(root.resolve()),
        "git_remote": git_remote(root),
        "platform": platform.system().lower(),
        "node_entrypoint": str((root / "bin" / "motionloom.mjs").resolve()),
        "canonical_skill": str((root / "SKILL.md").resolve()),
    }


def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    root = root.resolve()
    manifest_path = root / "agent-surfaces.json"

    if not manifest_path.is_file():
        return {"status": "fail", "errors": ["missing agent-surfaces.json"], "warnings": [], "root": str(root)}

    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "fail", "errors": [f"invalid agent-surfaces.json: {exc}"], "warnings": [], "root": str(root)}

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {manifest.get('schema_version')!r}")
    package = read_package(root)
    if manifest.get("name") != package.get("name"):
        errors.append("manifest name does not match package.json")
    if manifest.get("version") != package.get("version"):
        errors.append("manifest version does not match package.json")
    if manifest.get("canonical") != {
        "skill": "SKILL.md",
        "agent_card": "agent-card.json",
        "cli": "bin/motionloom.mjs",
    }:
        errors.append("canonical paths do not match the package contract")

    for required in ("SKILL.md", "agent-card.json", "bin/motionloom.mjs", "package.json"):
        path = root / required
        if not path.is_file():
            errors.append(f"missing canonical file: {required}")

    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("surfaces must be a non-empty array")
        surfaces = []
    ids: set[str] = set()
    paths: set[str] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            errors.append("surface entry must be an object")
            continue
        surface_id = surface.get("id")
        surface_path = surface.get("path")
        if surface_id in ids:
            errors.append(f"duplicate surface id: {surface_id}")
        if isinstance(surface_id, str):
            ids.add(surface_id)
        if not isinstance(surface_path, str) or surface_path.startswith("/") or ".." in Path(surface_path).parts:
            errors.append(f"surface path is not safe: {surface_path!r}")
            continue
        if surface_path in paths:
            errors.append(f"duplicate surface path: {surface_path}")
        paths.add(surface_path)
        file_path = root / surface_path
        if not file_path.is_file():
            errors.append(f"missing surface file: {surface_path}")
        if file_path.is_symlink():
            errors.append(f"symlinked surface is not portable: {surface_path}")
        if surface.get("canonical") != "SKILL.md":
            errors.append(f"surface {surface_id!r} does not point to SKILL.md")
        if surface.get("load_mode") not in {"alias", "router"}:
            errors.append(f"surface {surface_id!r} has invalid load_mode")
        if not isinstance(surface.get("agents"), list) or not surface.get("agents"):
            errors.append(f"surface {surface_id!r} has no supported agents")

    installations = manifest.get("installations")
    if not isinstance(installations, list) or not installations:
        errors.append("installations must be a non-empty array")
        installations = []
    installation_ids: set[str] = set()
    for item in installations:
        if not isinstance(item, dict):
            errors.append("installation entry must be an object")
            continue
        item_id = item.get("id")
        if item_id in installation_ids:
            errors.append(f"duplicate installation id: {item_id}")
        if isinstance(item_id, str):
            installation_ids.add(item_id)
        for key in ("source_kind", "command", "verification", "provenance"):
            if not item.get(key):
                errors.append(f"installation {item_id!r} missing {key}")

    compatibility = manifest.get("compatibility", {})
    for key in ("operating_systems", "node", "python", "agents"):
        if not compatibility.get(key):
            errors.append(f"compatibility missing {key}")
    rules = manifest.get("rules", {})
    if rules.get("canonical_instruction_source") != "SKILL.md":
        errors.append("canonical_instruction_source must be SKILL.md")
    for key in ("no_surface_copy", "no_network_required_for_check", "approval_is_never_inferred"):
        if rules.get(key) is not True:
            errors.append(f"rule {key} must remain true")

    package_files = package.get("files", [])
    for required_package_path in ("agent-surfaces.json", ".agents", ".claude", ".codex", "AGENTS.md"):
        if required_package_path not in package_files:
            warnings.append(f"package.json files does not explicitly include {required_package_path}")

    return {
        "status": "pass" if not errors else "fail",
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "source": source_identity(root),
        "surface_count": len(surfaces),
        "installation_count": len(installations),
        "errors": errors,
        "warnings": warnings,
    }


def install_matrix(root: Path) -> dict[str, Any]:
    result = validate(root)
    manifest = load_json(root / "agent-surfaces.json") if (root / "agent-surfaces.json").is_file() else {}
    rows = []
    for item in manifest.get("installations", []):
        rows.append({
            "id": item.get("id"),
            "source_kind": item.get("source_kind"),
            "command": item.get("command"),
            "verification": item.get("verification"),
            "provenance": item.get("provenance"),
            "status": "available" if result.get("status") == "pass" else "blocked_by_contract",
        })
    return {"status": result.get("status"), "matrix": rows, "compatibility": manifest.get("compatibility", {}), "errors": result.get("errors", [])}


def parser() -> argparse.ArgumentParser:
    root_default = str(repo_root())
    command = argparse.ArgumentParser(prog="motionloom discovery", description=__doc__)
    sub = command.add_subparsers(dest="action", required=True)
    for name, help_text in (
        ("check", "Validate Agent surfaces and installation contract"),
        ("show", "Print the canonical discovery manifest"),
        ("source", "Print source identity for this checkout"),
        ("install-matrix", "Print supported installation sources and verification commands"),
    ):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--root", default=root_default, help="MotionLoom checkout root")
        child.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if args.action == "check":
        result = validate(root)
    elif args.action == "show":
        try:
            result = load_json(root / "agent-surfaces.json")
        except (OSError, json.JSONDecodeError) as exc:
            result = {"status": "fail", "errors": [str(exc)]}
    elif args.action == "source":
        result = source_identity(root)
    else:
        result = install_matrix(root)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.action == "show":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.action == "source":
            print(f"{result.get('name')}@{result.get('version')} — {result.get('platform')} — {result.get('root')}")
            if result.get("git_remote"):
                print(f"remote: {result['git_remote']}")
        elif args.action == "install-matrix":
            print(f"installation matrix: {result.get('status')}")
            for row in result.get("matrix", []):
                print(f"- {row['id']}: {row['command']} -> {row['verification']}")
        else:
            print(f"discovery contract: {result.get('status')}")
            for error in result.get("errors", []):
                print(f"error: {error}")
            for warning in result.get("warnings", []):
                print(f"warning: {warning}")
    return EXIT_OK if result.get("status") in {None, "pass"} else EXIT_INVALID


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(EXIT_USAGE)
