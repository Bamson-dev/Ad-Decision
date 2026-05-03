#!/usr/bin/env bash
# Runs when a Cursor agent stops: commit tracked changes and push to origin.
# Logs on stderr; stdout is hook JSON for Cursor.

set -euo pipefail

log() { echo "[agent-git-push] $*" >&2; }

input=$(cat)
status=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('status') or '')
except Exception:
    print('')
" 2>/dev/null || true)

if [[ "$status" == "aborted" || "$status" == "error" ]]; then
  log "skip (agent status=$status)"
  printf '%s\n' '{}'
  exit 0
fi

root=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    roots = d.get('workspace_roots') or []
    print(roots[0] if roots else '')
except Exception:
    print('')
" 2>/dev/null || true)

if [[ -n "$root" ]]; then
  cd "$root" || { log "cannot cd to $root"; printf '%s\n' '{}'; exit 0; }
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  log "not a git repository"
  printf '%s\n' '{}'
  exit 0
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  log "no git remote 'origin'; add: git remote add origin <url>"
  printf '%s\n' '{}'
  exit 0
fi

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  git add -A
  if git diff --cached --quiet; then
    log "working tree dirty but nothing stageable (check .gitignore)"
  else
    msg="chore(cursor): agent update $(date -u +%Y-%m-%dT%H:%MZ)"
    if ! git commit -m "$msg"; then
      log "commit failed"
    fi
  fi
fi

if ! out=$(git push origin HEAD 2>&1); then
  log "git push failed — set up SSH/HTTPS auth for GitHub"
  log "$out"
else
  [[ -n "$out" ]] && log "$out"
fi

printf '%s\n' '{}'
exit 0
