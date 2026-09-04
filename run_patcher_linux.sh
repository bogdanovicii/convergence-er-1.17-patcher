#!/bin/bash
# Steam Deck / Linux helper for apply_1.17_patch.py.
#   bash run_patcher_linux.sh "/path/to/ConvergenceER" ["/path/to/ELDEN RING/Game"]
#
# Needs only python3 plus the `zstd` and `openssl` command-line tools, which SteamOS and nearly every
# Linux distribution already have. No pip, no packages, nothing installed. (If the optional Python modules
# zstandard + cryptography happen to be present they are used instead; the result is identical.)
set -uo pipefail
cd "$(dirname "$(realpath "$0")")"
if [[ $# -lt 1 ]]; then echo "usage: bash $0 <ConvergenceER folder> [<Game folder>]"; exit 2; fi
command -v python3 >/dev/null || { echo "[FAIL] python3 not found"; exit 1; }
if python3 -c "import zstandard, cryptography" 2>/dev/null; then
  echo "[ ok ] Python modules present"
elif command -v zstd >/dev/null && command -v openssl >/dev/null; then
  echo "[ ok ] using the system's zstd + openssl tools (no Python packages needed)"
else
  echo "[info] no Python modules and no zstd/openssl tools - trying a user-local pip install ..."
  if ! python3 -m pip --version >/dev/null 2>&1; then
    tmp=$(mktemp -d)
    if curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$tmp/get-pip.py"; then
      python3 "$tmp/get-pip.py" --user -q --break-system-packages 2>/dev/null || python3 "$tmp/get-pip.py" --user -q 2>/dev/null || true
    fi
    rm -rf "$tmp"
  fi
  python3 -m pip install --user -q --break-system-packages zstandard cryptography 2>/dev/null \
    || python3 -m pip install --user -q zstandard cryptography 2>/dev/null || true
  python3 -c "import zstandard, cryptography" 2>/dev/null || {
    echo "[FAIL] could not get either the Python modules or the zstd + openssl tools."
    echo "       Install zstd and openssl (e.g. 'sudo pacman -S zstd openssl' on Arch, 'sudo apt install zstd openssl' on Debian/Ubuntu) and run again."
    exit 1; }
fi
exec python3 apply_1.17_patch.py "$@"
