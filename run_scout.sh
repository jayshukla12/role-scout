#!/bin/bash
# Move to the script's directory
cd "$(dirname "$0")"

echo "=== Starting Agent Run at $(date) ==="
# Use the local python environment if available, otherwise fallback to system python
python3 scout.py
echo "=== Finished Agent Run at $(date) ==="
