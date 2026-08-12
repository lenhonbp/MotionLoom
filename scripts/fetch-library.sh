#!/usr/bin/env bash
# fetch-library.sh — Pull vetted open-source animation assets into
# assets/library/ from official public sources. Every asset is recorded
# with its license and source URL in assets/library/ATTRIBUTION.md so the
# PR review can verify provenance.
#
# Usage: bash scripts/fetch-library.sh
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$SCRIPT_DIR/../assets/library"
mkdir -p "$LIB"

ATTR="$LIB/ATTRIBUTION.md"
echo "# Asset Library Attribution" > "$ATTR"
echo "" >> "$ATTR"
echo "| Asset | Source | License | Downloaded |" >> "$ATTR"
echo "|---|---|---|---|" >> "$ATTR"

fetch() {
  local name="$1" url="$2" source="$3" license="$4"
  local out="$LIB/$name"
  if curl -sfL -o "$out" "$url"; then
    local ok
    ok=$(python3 - "$out" <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print("v=%s fr=%s op=%s layers=%d" % (d.get("v"), d.get("fr"), d.get("op"), len(d.get("layers", []))))
except Exception as e:
    print("INVALID: %s" % e)
    sys.exit(1)
EOF
    ) || { rm -f "$out"; echo "  [skip] $name invalid"; return; }
    echo "| \`$name\` | $source | $license | $ok |" >> "$ATTR"
    echo "  [ok] $name ($ok)"
  else
    echo "  [fail] $name"
  fi
}

echo "== Fetching vetted open Lottie assets =="
fetch "loading-dots.json" \
  "https://assets1.lottiefiles.com/packages/lf20_owfp8w4p.json" \
  "https://lottiefiles.com/free-animation/loading" \
  "LottieFiles Free (check per-asset license page)"
fetch "success-check.json" \
  "https://assets2.lottiefiles.com/packages/lf20_qp1q7mct.json" \
  "https://lottiefiles.com/free-animation/success-check" \
  "LottieFiles Free (check per-asset license page)"
fetch "error-alert.json" \
  "https://assets5.lottiefiles.com/packages/lf20_u4yrau.json" \
  "https://lottiefiles.com/free-animation/error-alert" \
  "LottieFiles Free (check per-asset license page)"

echo ""
echo "Update URLs above with current vetted assets; always verify the license page"
echo "before shipping. Attribution table -> $ATTR"
