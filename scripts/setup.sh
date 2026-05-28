#!/usr/bin/env bash
set -euo pipefail

echo "Setting up Nexus Knowledge Engine..."

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "Setup complete. Activate the environment with: source .venv/bin/activate"
