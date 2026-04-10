#!/bin/bash
# Ensures all paths are available, including user site-packages where Playwright/Anthropic are installed.
export PATH="/Users/jayshukla/Library/Python/3.9/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "/Users/jayshukla/Desktop/AI Explorations/role-hunter"

echo "=== Starting Agent Run at $(date) ==="
/usr/bin/python3 scout.py
echo "=== Finished Agent Run at $(date) ==="
