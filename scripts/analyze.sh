#!/usr/bin/env bash
# analyze.sh — Step 1 of the pipeline: understand the host project.
# Emits project-context.json inside the analyzed project root.
#
# Usage: bash scripts/analyze.sh <project-path>
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="${1:-.}"

python3 "$SCRIPT_DIR/../src/core/analyzer.py" "$PROJECT" --output "$(cd "$PROJECT" 2>/dev/null && pwd)/project-context.json"
echo ""
echo "== Step 1 complete: the target project's project-context.json is now the binding source =="
echo "   Review inferred values (marked as assumptions) before generating."
