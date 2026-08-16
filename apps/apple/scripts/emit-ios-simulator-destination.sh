#!/usr/bin/env sh
# MotionLoom Apple CI: generate a local SDK-specific SwiftPM destination; do not commit machine paths.
set -eu

output_path="${1:?usage: emit-ios-simulator-destination.sh OUTPUT_PATH}"
sdk_path="$(xcrun --sdk iphonesimulator --show-sdk-path)"
swiftc_path="$(xcrun --find swiftc)"
toolchain_bin_dir="$(dirname "$swiftc_path")"
sdk_version="$(xcrun --sdk iphonesimulator --show-sdk-platform-version)"

cat > "$output_path" <<EOF
{
  "version": 1,
  "sdk": "$sdk_path",
  "toolchain-bin-dir": "$toolchain_bin_dir",
  "target": "arm64-apple-ios${sdk_version}-simulator",
  "extra-cc-flags": [],
  "extra-swiftc-flags": [],
  "extra-cpp-flags": [],
  "extra-linker-flags": []
}
EOF
