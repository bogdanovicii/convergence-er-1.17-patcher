#!/bin/bash
# Start_Convergence.sh - launch The Convergence on Linux / Steam Deck (SteamOS).
#
# Alternative to Start_Convergence.bat for Linux users who prefer me3's native
# Linux binary (the .bat run through Proton is the recommended route; see
# README.md). This script mirrors me3's own launch-eldenring-mods.sh from the
# official Linux release: it runs the native me3 binary and points it at the
# bundled Windows binaries with --windows-binaries-dir.
#
# Usage:  ./Start_Convergence.sh            normal launch
#         ./Start_Convergence.sh -v         verbose (trace) logging for debugging

set -uo pipefail

cd "$(dirname "$(realpath "$0")")" || exit 1
here=$(pwd)

ME3_BIN="$here/me3/Linux/me3"
WIN_DIR="$here/me3/Linux/win64"

if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then
    export ME3_CONSOLE_LOG_LEVEL=trace
    export ME3_FILE_LOG_LEVEL=trace
    echo "[info] verbose logging enabled"
else
    export ME3_CONSOLE_LOG_LEVEL="${ME3_CONSOLE_LOG_LEVEL:-info}"
fi

# --- sanity checks -----------------------------------------------------------

fail() { echo "[FAIL] $*" >&2; exit 1; }

[[ -f "$ME3_BIN" ]] || fail "missing $ME3_BIN - copy the whole ConvergenceER folder, not just parts of it."
[[ -d "$WIN_DIR" ]] || fail "missing $WIN_DIR (me3's Windows binaries)."
for f in me3-launcher.exe me3_mod_host.dll; do
    [[ -f "$WIN_DIR/$f" ]] || fail "missing $WIN_DIR/$f"
done

# Copying from exFAT/NTFS (e.g. an external SSD) loses the executable bit.
if [[ ! -x "$ME3_BIN" ]]; then
    echo "[info] me3 binary is not executable, fixing (chmod +x)"
    chmod +x "$ME3_BIN" 2>/dev/null || fail "could not chmod +x $ME3_BIN - is this folder on a noexec/exFAT mount? Copy it to your home directory (e.g. ~/ConvergenceER) and run it from there."
fi

# Probe that the binary can actually run. A noexec mount (external exFAT/NTFS
# drive, Flatpak-restricted path) is the usual cause of failure here.
if ver=$("$ME3_BIN" --version 2>&1); then
    echo "[ ok ] $(printf '%s' "$ver" | head -1)"
else
    echo "[warn] could not run '$ME3_BIN --version'. If the launch fails below, this folder is probably on a mount without exec permission (external exFAT/NTFS drive, or a Flatpak-restricted path); copy it to the internal drive, e.g. ~/ConvergenceER, and run it from there."
fi

# Warn if Steam is not running - me3 locates the Steam dir and a Proton runtime.
if ! pgrep -x steam >/dev/null 2>&1 && ! pgrep -f 'steamwebhelper' >/dev/null 2>&1; then
    echo "[warn] Steam does not appear to be running. me3 needs Steam (with Elden Ring installed and owned) to start the game through Proton. Start Steam first if the launch fails."
fi

# --- pick the profile, same rule as the .bat ---------------------------------

PROFILE="$here/me3/convergence.me3"
echo "[info] launching The Convergence"
[[ -f "$PROFILE" ]] || fail "profile not found: $PROFILE"

# --- report what we are about to load ----------------------------------------

if [[ -f "$here/mod/regulation.bin" ]]; then
    sz=$(stat -c %s "$here/mod/regulation.bin" 2>/dev/null || stat -f %z "$here/mod/regulation.bin")
    case "$sz" in
        2975152) echo "[ ok ] mod/regulation.bin is the 1.17 build" ;;
        2964304) echo "[warn] mod/regulation.bin is the stock 1.16 build - on game 1.17 the title screen will say Regulation Ver. 1.16 and Torrent will not work. See README.md." ;;
        *)       echo "[info] mod/regulation.bin: $sz bytes" ;;
    esac
fi

echo "[info] logs: \${XDG_DATA_HOME:-~/.local/share}/me3/me3-logs (newest file)"
echo

# --- launch ------------------------------------------------------------------
# This is the same invocation shape as me3's official launch-eldenring-mods.sh.

exec "$ME3_BIN" \
    --windows-binaries-dir "$WIN_DIR" \
    launch \
    --auto-detect \
    -p "$PROFILE"
