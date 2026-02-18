#!/bin/bash
# deploy.sh - Sync project to server while respecting .rsync-filter

# Exit on error
set -e

# Variables
LOCAL_DIR="$(pwd)/"
REMOTE_USER="root"
REMOTE_HOST="206.189.112.140"
REMOTE_DIR="/home/safe-ai"

echo "🚀 Deploying from $LOCAL_DIR to $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

# Dry run option
if [ "$1" == "--dry-run" ]; then
  echo "🔍 Running in dry run mode..."
  rsync -avz --dry-run --delete --filter='merge .rsync-filter' "$LOCAL_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
else
  rsync -avz --delete --filter='merge .rsync-filter' "$LOCAL_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
  echo "✅ Deployment complete!"
fi
