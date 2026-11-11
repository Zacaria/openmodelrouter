#!/bin/sh
# Isolated native Linux replay. Never use a personal HOME/XDG profile.
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
: "${OMR_TEST_APP:?Set OMR_TEST_APP to the exact native application binary}"
: "${OMR_TAURI_DRIVER:?Set OMR_TAURI_DRIVER to tauri-driver 2.1.0}"
: "${OMR_WEBKIT_DRIVER:?Set OMR_WEBKIT_DRIVER to WebKitWebDriver}"
export OMR_TEST_APP OMR_TAURI_DRIVER OMR_WEBKIT_DRIVER
OMR_EVIDENCE=${OMR_EVIDENCE:-"$ROOT/.evidence/native"}
export OMR_EVIDENCE
mkdir -p "$ROOT/.native-test" "$OMR_EVIDENCE"
RUN=$(mktemp -d "$ROOT/.native-test/replay-XXXXXX")
export OMR_RUN="$RUN" OMR_ROOT="$ROOT" UV_CACHE_DIR="$ROOT/.native-test/uv-cache"
RUNTIME=$(mktemp -d "${TMPDIR:?Set TMPDIR to a short managed scratch directory}/omr-XXXXXX")
# sockaddr_un.sun_path is bounded (108 bytes on Linux), unlike worktree paths.
if [ "${#RUNTIME}" -gt 85 ]; then
  printf '%s\n' 'TMPDIR is too long for isolated Secret Service sockets' >&2
  rmdir "$RUNTIME"
  exit 2
fi
mkdir -p "$RUN/home" "$RUN/data" "$RUN/config" "$RUN/cache" "$RUN/tmp"
export HOME="$RUN/home" XDG_DATA_HOME="$RUN/data" XDG_CONFIG_HOME="$RUN/config" XDG_CACHE_HOME="$RUN/cache" TMPDIR="$RUN/tmp" XDG_RUNTIME_DIR="$RUNTIME" GNOME_KEYRING_CONTROL="$RUNTIME/keyring"
dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' sh -c '
  xfwm4 --compositor=off > "$OMR_RUN/window-manager.log" 2>&1 &
  WM=$!
  if [ "${OMR_TEST_DARK:-0}" = 1 ]; then
    gsettings set org.gnome.desktop.interface color-scheme prefer-dark
    export GTK_THEME=Adwaita:dark
  fi
  if [ "${OMR_TEST_UNLOCK_KEYRING:-0}" = 1 ]; then
    printf "%s" "SYNTHETIC-TEST-KEYRING-PASSWORD" | gnome-keyring-daemon --unlock --components=secrets --control-directory "$GNOME_KEYRING_CONTROL" > "$OMR_RUN/keyring.log" 2>&1
  fi
  "$OMR_TAURI_DRIVER" --port "${OMR_TEST_DRIVER_PORT:-4444}" --native-port "${OMR_TEST_WEBKIT_PORT:-4445}" --native-driver "$OMR_WEBKIT_DRIVER" > "$OMR_RUN/driver.log" 2>&1 &
  DRIVER=$!
  trap "kill $DRIVER $WM 2>/dev/null || true" EXIT
  REPLAY=native_replay.py
  if [ "${OMR_NATIVE_UI_REPLAY:-0}" = 1 ]; then
    REPLAY=native_strategies_ui.py
  fi
  uv run --python 3.13.5 --with selenium==4.38.0 python "$OMR_ROOT/scripts/$REPLAY"
'
