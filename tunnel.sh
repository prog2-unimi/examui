#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  Massimo Santini
#
# Termux client script: opens SSH tunnel, launches browser, cleans up on exit.
# Requires: openssh, termux-api (pkg install openssh termux-api)

HOST=svm
KEY=~/.ssh/id_examui
PORT=8765

# Open tunnel; server's authorized_keys command= starts gunicorn automatically
unset SSH_AUTH_SOCK SSH_AGENT_PID
ssh -i "$KEY" -o IdentitiesOnly=yes -L "${PORT}:localhost:${PORT}" "$HOST" < <(sleep infinity) 2>&1 &
SSH_PID=$!
echo "SSH pid=$SSH_PID"

trap "kill $SSH_PID 2>/dev/null; wait $SSH_PID 2>/dev/null" EXIT INT TERM

# Wait until the tunnel is actually accepting connections
echo "Connecting…"
for i in $(seq 1 15); do
    if nc -z localhost "$PORT" 2>/dev/null; then
        break
    fi
    if ! kill -0 "$SSH_PID" 2>/dev/null; then
        echo "SSH process died — check key/host config" >&2
        exit 1
    fi
    sleep 1
done

termux-open-url "http://localhost:${PORT}"

# Keep the tunnel alive until Ctrl-C
echo "Tunnel open — press Ctrl-C to disconnect"
wait "$SSH_PID"
