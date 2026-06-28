#!/usr/bin/env bash
# Install Phase 3 background automation (runs pipeline every 6 hours on macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SRC="$ROOT/scripts/com.fillviz.news-automation.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.fillviz.news-automation.plist"
LABEL="com.fillviz.news-automation"

chmod +x "$ROOT/scripts/run_pipeline.sh"
chmod +x "$ROOT/scripts/run_discovery.sh"

mkdir -p "$ROOT/output"
mkdir -p "$HOME/Library/LaunchAgents"

# Replace hardcoded paths if project was moved
sed "s|/Users/mehulwadhavekar/Desktop/Cursor Projects/News channel Automationa|$ROOT|g" \
  "$PLIST_SRC" > "$PLIST_DEST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Automation installed."
echo "  Runs every 6 hours + once now"
echo "  Log: $ROOT/output/automation.log"
echo ""
echo "Commands:"
echo "  Stop:    launchctl bootout gui/$(id -u)/$LABEL"
echo "  Start:   launchctl bootstrap gui/$(id -u)/ $PLIST_DEST"
echo "  Manual:  $ROOT/scripts/run_pipeline.sh"
