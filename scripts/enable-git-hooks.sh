#!/usr/bin/env bash
# One-time setup: enable secret-blocking pre-commit hook for this repo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chmod +x "$ROOT/.githooks/pre-commit"
git -C "$ROOT" config core.hooksPath .githooks
echo "Pre-commit hook enabled. Secret files (.env, credentials/) cannot be committed."
