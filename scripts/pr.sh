#!/usr/bin/env bash
# pr.sh — Step 6 of the pipeline: confirm-into-PR.
# Commits the rendered scene (animation file, manifest, snapshots, signed
# spec) to a fix/<scene> branch and opens the pull request via the gh CLI.
#
# Usage: bash scripts/pr.sh <scene> [title]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"
SCENE="${1:?usage: bash scripts/pr.sh <scene> [title]}"
TITLE="${2:-"animation: scene '$SCENE' (verified in Dev Lab)"}"
SCENE_DIR="$REPO/src/output/$SCENE"
CONTEXT_PATH="${CONTEXT_PATH:-$REPO/project-context.json}"
TASK_DIR="${TASK_DIR:-}"

cd "$REPO"

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "error: scripts/pr.sh must run inside a Git clone" >&2
  exit 1
fi

if [ ! -d "$SCENE_DIR" ]; then
  echo "error: scene directory not found: $SCENE_DIR"
  exit 1
fi

if [[ ! "$SCENE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: scene id contains unsafe branch/path characters: $SCENE" >&2
  exit 1
fi

echo "== running context-bound quality gate =="
QUALITY_ARGS=(--scene "$SCENE" --context "$CONTEXT_PATH" --require-browser-review)
if [ -n "$TASK_DIR" ]; then
  QUALITY_ARGS+=(--task-dir "$TASK_DIR")
else
  echo "error: TASK_DIR is required; browser Agent must persist review.json before PR" >&2
  exit 1
fi
python3 "$REPO/scripts/quality-gate.py" "${QUALITY_ARGS[@]}"
python3 "$REPO/scripts/review-hook.py" validate --task-dir "$TASK_DIR"

BRANCH="fix/$SCENE"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
git add "src/output/$SCENE"
if git diff --cached --quiet; then
  echo "error: no staged scene changes to commit" >&2
  exit 1
fi
git commit -m "feat(animation): scene '$SCENE' — proven in Dev Lab

- motion-spec signed (see src/output/$SCENE/motion-spec.json)
- snapshot frames: 0/50/100% in src/output/$SCENE/snapshot/
- context-bound quality gate: passed
- brand tokens bound from $CONTEXT_PATH"

if [ "${OPEN_PR:-1}" != "1" ]; then
  echo "== committed to $BRANCH — OPEN_PR=0, push/open PR manually =="
  exit 0
fi

if ! command -v gh &>/dev/null; then
  echo "== committed to $BRANCH — install gh CLI to open the PR =="
  echo "   git push origin $BRANCH"
  exit 0
fi

git push -u origin "$BRANCH" 2>/dev/null
gh pr create \
  --title "$TITLE" \
  --body "## Scene: $SCENE

Verified in the Dev Lab (checklist + snapshot diffs attached).
Framework, duration, easing, reduced-motion policy and theme tokens per the signed motion spec.

### Snapshots
| 0% | 50% | 100% |
|---|---|---|
| \`snapshot/frame-00.png\` | \`snapshot/frame-50.png\` | \`snapshot/frame-100.png\` |

Ready to review — comment fixes in the Dev Lab or approve to merge." \
  && echo "== PR opened for scene: $SCENE =="
