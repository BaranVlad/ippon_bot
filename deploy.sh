#!/bin/bash
set -e

PROJECT_DIR="/home/bladvaran/projects/ippon_bot"
SERVICE_NAME="ippon-bot"

echo "[deploy] Pulling latest changes..."
git -C "$PROJECT_DIR" pull origin main

echo "[deploy] Activating venv and installing dependencies..."
source "$PROJECT_DIR/.venv/bin/activate"
pip install -q -r "$PROJECT_DIR/requirements.txt"

echo "[deploy] Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

echo "[deploy] Done! Checking status..."
sudo systemctl status --no-pager "$SERVICE_NAME"
