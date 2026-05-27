#!/bin/bash
set -e

PROJECT_DIR="/home/bladvaran/projects/ippon_bot"
SERVICE_NAME="ippon-bot"

cd "$PROJECT_DIR"

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [ -z "$REMOTE" ]; then
    echo "[deploy] No upstream branch configured, running git pull anyway..."
elif [ "$LOCAL" = "$REMOTE" ]; then
    echo "[deploy] Already up to date. Nothing to deploy."
    exit 0
fi

echo "[deploy] Pulling latest changes..."
git pull origin main

echo "[deploy] Activating venv and installing dependencies..."
source "$PROJECT_DIR/.venv/bin/activate"
pip install -q -r "$PROJECT_DIR/requirements.txt"

echo "[deploy] Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

echo "[deploy] Done! Checking status..."
sudo systemctl status --no-pager "$SERVICE_NAME"
