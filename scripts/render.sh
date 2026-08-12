#!/usr/bin/env bash
# render.sh — Step 5 of the pipeline: render deterministic snapshot frames
# (0%, 50%, 100%) of a scene for visual verification and PR attachments.
#
# Usage: bash scripts/render.sh <scene>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"
SCENE="${1:?usage: bash scripts/render.sh <scene>}"
SCENE_DIR="$REPO/src/output/$SCENE"

if [[ ! "$SCENE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: scene id contains unsafe path characters: $SCENE" >&2
  exit 1
fi

if [ ! -d "$SCENE_DIR" ]; then
  echo "error: scene directory not found: $SCENE_DIR"
  exit 1
fi

mkdir -p "$SCENE_DIR/snapshot"

EXTRA_ARGS=()
if [ "${ALLOW_PLACEHOLDER:-0}" = "1" ]; then
  EXTRA_ARGS+=(--allow-placeholder)
fi

python3 "$REPO/src/core/snapshot.py" render "$SCENE" \
  --scene-dir "$SCENE_DIR" \
  --progress 0,50,100 "${EXTRA_ARGS[@]}"

if [ ! -f "$SCENE_DIR/snapshot/.render-meta.json" ]; then
  echo "error: renderer did not write snapshot metadata" >&2
  exit 1
fi
echo "== runtime snapshots written to $SCENE_DIR/snapshot =="
