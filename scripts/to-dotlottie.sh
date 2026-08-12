#!/usr/bin/env bash
# Package a validated scene into a dotLottie v2 archive.
# Usage: bash scripts/to-dotlottie.sh <scene> [output.lottie]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"
SCENE="${1:?usage: bash scripts/to-dotlottie.sh <scene> [output.lottie]}"
OUT="${2:-$REPO/src/output/$SCENE/animation.lottie}"

if [[ ! "$SCENE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: scene id contains unsafe path characters: $SCENE" >&2
  exit 1
fi

SCENE_DIR="$REPO/src/output/$SCENE"
if [[ ! -d "$SCENE_DIR" ]]; then
  echo "error: scene directory not found: $SCENE_DIR" >&2
  exit 1
fi

node "$SCRIPT_DIR/to-dotlottie.mjs" \
  --scene-dir "$SCENE_DIR" \
  --output "$OUT" \
  --generator "animation-skill-kit/to-dotlottie@1.0.0"
