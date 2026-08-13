#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENE="${1:?scene is required}"
TASK_DIR="${2:?task directory is required}"

if [[ ! "$SCENE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "capture-runtime-telemetry: unsafe scene identifier: $SCENE" >&2
  exit 2
fi
if [[ ! -f "$ROOT/src/output/$SCENE/manifest.json" || ! -f "$ROOT/$TASK_DIR/task.json" ]]; then
  echo "capture-runtime-telemetry: missing scene manifest or task.json" >&2
  exit 2
fi

MANIFEST="$ROOT/src/output/$SCENE/manifest.json"
TASK_JSON="$ROOT/$TASK_DIR/task.json"
SOURCE_FILE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["file"])' "$MANIFEST")"
TASK_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["task_id"])' "$TASK_JSON")"
OUTPUT_DIR="$ROOT/$TASK_DIR/runtime-adapters"

rm -rf "$OUTPUT_DIR"
RUNTIME_EVIDENCE_DIR="$OUTPUT_DIR" \
RUNTIME_SCENE="$SCENE" \
RUNTIME_TASK_ID="$TASK_ID" \
RUNTIME_SOURCE_PATH="$ROOT/src/output/$SCENE/$SOURCE_FILE" \
RUNTIME_MANIFEST_PATH="$MANIFEST" \
RUNTIME_MOTION_IR_PATH="$ROOT/$TASK_DIR/motion-ir.json" \
  npm run runtime:test

python3 "$ROOT/scripts/evidence-verifier.py" \
  --scene-dir "$ROOT/src/output/$SCENE" \
  --task-dir "$ROOT/$TASK_DIR" \
  --runtime-evidence runtime-adapters/runtime-evidence.json \
  --max-age-days 1 \
  --output "$ROOT/$TASK_DIR/evidence-verifier-report.json"
