#!/usr/bin/env bash
# Stop local Mac automation — use GitHub Actions instead.
set -euo pipefail
LABEL="com.fillviz.news-automation"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "Local automation stopped." || echo "Local automation was not running."
