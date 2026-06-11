#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  Massimo Santini
#
# Intended as the command= entry in ~/.ssh/authorized_keys:
#
#   command="/path/to/ssh_start.sh",no-pty,no-agent-forwarding,\
#   no-X11-forwarding,permitopen="localhost:8765" ssh-rsa AAAA...
#
# The server starts when the tunnel is established and is killed when
# the SSH connection closes.

exec >> /tmp/examui_ssh_debug.log 2>&1
set -xe

# Save the SSH channel stdin BEFORE any background job is launched.
# In a non-interactive shell, bash silently redirects fd 0 of background
# processes to /dev/null; saving it here lets the watchdog read from the
# real channel rather than from /dev/null.
exec 9<&0

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

APPDIR="$(dirname "$(realpath "$0")")"
PIDFILE="$APPDIR/.gunicorn.pid"
LOGFILE="$APPDIR/ssh_start.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOGFILE"; }

log "--- session start (SSH_CLIENT=${SSH_CLIENT:-unknown}) ---"

if [ ! -f "$APPDIR/.envrc" ]; then
    log "ERROR: $APPDIR/.envrc not found"
    exit 1
fi
# shellcheck source=.envrc
source "$APPDIR/.envrc"
log "sourced .envrc"

# Kill any leftover process from a previous session
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill "$OLD_PID" 2>/dev/null; then
        log "killed leftover gunicorn pid=$OLD_PID"
    else
        log "stale pidfile (pid=$OLD_PID already gone)"
    fi
    rm -f "$PIDFILE"
fi

# Start gunicorn in the background; --pid makes gunicorn write its own master PID
cd "$APPDIR"
log "starting gunicorn (HISTORY_DIR=$HISTORY_DIR EVALS_DIR=$EVALS_DIR STUDENT_BASE=$STUDENT_BASE)"
HISTORY_DIR="$HISTORY_DIR" EVALS_DIR="$EVALS_DIR" STUDENT_BASE="$STUDENT_BASE" \
    uv run gunicorn --workers=1 --bind=127.0.0.1:8765 --pid "$PIDFILE" 'examui:create_app()' \
    >> "$LOGFILE" 2>&1 &
UV_PID=$!

# Wait for gunicorn to write its PID file (it does so after forking)
for i in $(seq 1 10); do
    [ -f "$PIDFILE" ] && break
    sleep 0.5
done
GUNICORN_PID=$(cat "$PIDFILE" 2>/dev/null || echo "$UV_PID")
log "gunicorn started pid=$GUNICORN_PID (uv wrapper pid=$UV_PID)"

# Guard against double-cleanup: SIGTERM fires the TERM trap, then the EXIT
# trap also fires when the script exits — without the flag, cleanup runs twice.
_cleaned=0
cleanup() {
    [ "$_cleaned" -eq 1 ] && return
    _cleaned=1
    log "cleanup: killing gunicorn pid=$GUNICORN_PID"
    kill "$GUNICORN_PID" 2>/dev/null || true
    rm -f "$PIDFILE"
    log "--- session end ---"
}
trap cleanup EXIT HUP TERM INT

# Watchdog: read from fd 9 (the saved SSH channel stdin); EOF = disconnect.
# Using <&9 is necessary because bash redirects fd 0 of background jobs
# to /dev/null in non-interactive shells, which would fire the watchdog
# immediately if we used plain "cat > /dev/null".
{ cat <&9 > /dev/null; kill -TERM "$$" 2>/dev/null; } &

# Block here until gunicorn exits or the watchdog kills us
wait "$UV_PID"
