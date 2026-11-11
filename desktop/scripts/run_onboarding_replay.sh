#!/bin/sh
# Real onboarding replay in a disposable, synthetic-only desktop session.
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
: "${OMR_TEST_APP:?Set exact native application path}"
: "${OMR_TAURI_DRIVER:?Set tauri-driver 2.1.0 path}"
: "${OMR_WEBKIT_DRIVER:?Set matching WebKitWebDriver path}"
: "${OMR_TEST_PYTHON:?Set qualification interpreter with Selenium 4.38.0}"
: "${TMPDIR:?Set managed scratch directory}"
export OMR_TEST_APP OMR_TAURI_DRIVER OMR_WEBKIT_DRIVER OMR_TEST_PYTHON
OMR_EVIDENCE=${OMR_EVIDENCE:-"$ROOT/.evidence/onboarding"}
export OMR_EVIDENCE
mkdir -p "$ROOT/.native-test" "$OMR_EVIDENCE"
RUN=$(mktemp -d "$ROOT/.native-test/onboarding-XXXXXX")
RUNTIME=$(mktemp -d "$TMPDIR/omr-onboard-XXXXXX")
if [ "${#RUNTIME}" -gt 85 ]; then
  printf '%s\n' 'Managed scratch path is too long for Secret Service sockets' >&2
  rmdir "$RUNTIME"
  exit 2
fi
export OMR_RUN="$RUN" OMR_ROOT="$ROOT"
mkdir -p "$RUN/home" "$RUN/data" "$RUN/config" "$RUN/cache" "$RUN/tmp"
export HOME="$RUN/home" XDG_DATA_HOME="$RUN/data" XDG_CONFIG_HOME="$RUN/config" XDG_CACHE_HOME="$RUN/cache" TMPDIR="$RUN/tmp" XDG_RUNTIME_DIR="$RUNTIME" GNOME_KEYRING_CONTROL="$RUNTIME/keyring"
printf '%s\n' "$RUN" > "$OMR_EVIDENCE/isolated-run-path.txt"
dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' sh -c '
  xfwm4 --compositor=off > "$OMR_RUN/window-manager.log" 2>&1 &
  WM=$!
  printf "%s" "SYNTHETIC-ONBOARDING-KEYRING-PASSWORD" | gnome-keyring-daemon --unlock --components=secrets --control-directory "$GNOME_KEYRING_CONTROL" > "$OMR_RUN/keyring.log" 2>&1
  "$OMR_TAURI_DRIVER" --port "${OMR_TEST_DRIVER_PORT:-4444}" --native-port "${OMR_TEST_WEBKIT_PORT:-4445}" --native-driver "$OMR_WEBKIT_DRIVER" > "$OMR_RUN/driver.log" 2>&1 &
  DRIVER=$!
  trap "kill $DRIVER $WM 2>/dev/null || true" EXIT
  "$OMR_TEST_PYTHON" "$OMR_ROOT/scripts/onboarding_replay.py"
'
