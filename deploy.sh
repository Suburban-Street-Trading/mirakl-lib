#!/bin/bash

REMOTE_USER="root"
REMOTE_IP="157.230.2.9"
REMOTE_DIR="/root/poetry/mirakl-lib"
PROJECT_DIR="/Users/samuelbenning/code/python/mirakl-lib"  # Set this to your project's root directory

echo "Syncing to remote droplet..."



rsync -avz --delete-before -e "ssh" \
    "$PROJECT_DIR/pyproject.toml" \
    "$PROJECT_DIR/poetry.lock" \
    "$PROJECT_DIR/README.md" \
    "${REMOTE_USER}@${REMOTE_IP}:${REMOTE_DIR}"

rsync -avz --delete-before -e "ssh" \
    --exclude="__pycache__/" \
    --exclude="*.pyc" \
    --exclude="/.mypy_cache/" \
    "$PROJECT_DIR/mirakl_lib/" \
    "${REMOTE_USER}@${REMOTE_IP}:${REMOTE_DIR}/mirakl_lib"
    
echo "Deployment completed."
