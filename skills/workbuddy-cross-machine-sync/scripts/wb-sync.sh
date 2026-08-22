#!/usr/bin/env bash
# Daily WorkBuddy sync helper for macOS / Linux.
#
#   wb-sync.sh pull    # before you start working
#   wb-sync.sh push    # after you finish
#   wb-sync.sh         # pull then push
#
# Install once:
#   chmod +x ~/.workbuddy/skills/workbuddy-cross-machine-sync/scripts/wb-sync.sh
#   ln -sf ~/.workbuddy/skills/workbuddy-cross-machine-sync/scripts/wb-sync.sh /usr/local/bin/wb-sync

set -uo pipefail

MODE="${1:-both}"
MSG="sync from $(hostname -s)"
REPOS=("$HOME/.workbuddy" "$HOME/WorkBuddy")

for repo in "${REPOS[@]}"; do
  echo ""
  echo "==> $repo"

  if [ ! -d "$repo/.git" ]; then
    echo "    [SKIP] not a git repository"
    continue
  fi

  cd "$repo" || continue

  if [ "$MODE" = "pull" ] || [ "$MODE" = "both" ]; then
    dirty=$(git status --porcelain)
    [ -n "$dirty" ] && git stash push -u -m 'wb-autosync' >/dev/null

    if ! git pull --rebase; then
      echo "    [FAIL] pull failed - resolve manually"
      # pull failed: restore the user's local changes we stashed above
      # so they are never stranded (the working tree is unchanged, so pop is safe).
      [ -n "$dirty" ] && { git stash pop >/dev/null 2>&1 && echo "    [OK] local changes restored from stash"; }
      continue
    fi

    if [ -n "$dirty" ]; then
      if ! git stash pop; then
        echo "    [WARN] stash pop hit a conflict - resolve, then re-run"
        continue
      fi
    fi
    echo "    [OK] pulled"
  fi

  if [ "$MODE" = "push" ] || [ "$MODE" = "both" ]; then
    if [ -n "$(git status --porcelain)" ]; then
      git add -A
      git commit -q -m "$MSG"
      if git push; then
        echo "    [OK] pushed"
      else
        echo "    [FAIL] push failed (auth? use a Personal Access Token as the password)"
      fi
    else
      echo "    [OK] nothing to commit"
    fi
  fi
done

echo ""
