#!/usr/bin/env bash
# devlab.sh — Step 5 of the pipeline: boot the Dev Lab for a scene.
# Copies the scene into the Dev Lab's public scenes folder, installs its
# dependencies, and serves the workbench so the user can scrub, inspect,
# run the checklist and iterate fixes before confirming.
#
# Usage: bash scripts/devlab.sh <scene>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"
SCENE="${1:?usage: bash scripts/devlab.sh <scene>}"
MODE="${2:-serve}"
SCENE_DIR="$REPO/src/output/$SCENE"
LAB="$REPO/dev-lab"

if [[ ! "$SCENE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: scene id contains unsafe path characters: $SCENE" >&2
  exit 1
fi

if [ ! -d "$SCENE_DIR" ]; then
  echo "error: scene directory not found: $SCENE_DIR"
  echo "run the generator first and render the scene into src/output/<scene>/"
  exit 1
fi

if [ ! -f "$SCENE_DIR/browser-review.json" ]; then
  echo "error: browser-review.json is required; run scripts/review-hook.py prepare after runtime render" >&2
  exit 1
fi

rm -rf "$LAB/public/scenes/$SCENE"
mkdir -p "$LAB/public/scenes/$SCENE"
cp -R "$SCENE_DIR"/. "$LAB/public/scenes/$SCENE/"

if [ "$MODE" = "--prepare-only" ]; then
  echo "== Dev Lab scene prepared: $LAB/public/scenes/$SCENE =="
  exit 0
fi

if [ ! -d "$LAB/node_modules" ]; then
  echo "== installing Dev Lab dependencies (first run) =="
  (cd "$LAB" && pnpm install --silent)
fi

PORT="${PORT:-3300}"
echo "== Dev Lab ready for scene: $SCENE =="
echo "   http://localhost:${PORT}/?scene=$SCENE (use the candidate URL emitted by review-hook.py for task-bound review)"
exec python3 -m http.server "$PORT" --directory "$LAB/public"
