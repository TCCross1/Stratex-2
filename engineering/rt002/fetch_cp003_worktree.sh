#!/usr/bin/env bash
# Fetch C-P-003 sources from audited PR #7 branch into a temp worktree for
# live claim tests. Does NOT modify or merge PR #7.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${RT002_CP003_WORKTREE:-/tmp/stratex-rt002-cp003}"
BRANCH="${RT002_CP003_BRANCH:-origin/cursor/lane1-cp003-publication-recovery}"
cd "$ROOT"
git fetch origin cursor/lane1-cp003-publication-recovery --prune 2>/dev/null || true
if [ -d "$DEST" ]; then
  echo "worktree exists: $DEST"
else
  git worktree add --detach "$DEST" "$BRANCH"
fi
echo "RT002_CP003_ROOT=$DEST"
echo "EXPECTED_HEAD=38671b2c23bf1b92f218046b9b519d7e13869ba0"
echo "ACTUAL_HEAD=$(git -C "$DEST" rev-parse HEAD)"
