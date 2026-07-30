---
name: workbuddy-cross-machine-sync
description: Set up and maintain cross-machine synchronization of WorkBuddy projects and user config (memory, skills, settings) between a macOS and a Windows PC using git or Syncthing. This skill should be used when the user wants to sync WorkBuddy data across two or more computers, asks how to keep projects consistent between a Mac and a Windows machine, or needs git-based or peer-to-peer sync instructions for WorkBuddy.
agent_created: true
---

# WorkBuddy 跨设备同步（macOS ↔ Windows）

## Purpose
Synchronize a user's WorkBuddy workspace across two computers (one macOS, one Windows) so that projects, conversation artifacts, memory, and skills stay consistent. Two strategies are provided: (1) git-based versioned sync via a private remote, and (2) Syncthing peer-to-peer continuous sync.

## When to use
- User asks "how to sync WorkBuddy between my Mac and Windows PC", "keep projects consistent across computers", or "set up git sync for WorkBuddy".
- User wants assistant memory/skills to follow them to another machine.
- User reports drift between machines and needs a reconciliation procedure.

## Directory map (verify before acting)
| Scope | macOS | Windows |
|-------|-------|---------|
| Projects base | `~/WorkBuddy` (`/Users/<user>/WorkBuddy`) | `%USERPROFILE%\WorkBuddy` (`C:\Users\<user>\WorkBuddy`) |
| Config home | `~/.workbuddy` | `%USERPROFILE%\.workbuddy` |

Always confirm the actual path on the Windows machine (open WorkBuddy and check where it stores projects) before cloning/merging, because the base folder name can differ.

## Critical rule (never violate)
Do **NOT** sync the SQLite database `workbuddy.db` (and its `-shm`/`-wal` sidecars) or any runtime cache (`logs/`, `sessions/`, `binaries/`, `blobs/`, `file-history/`, `traces/`, `shell-snapshots/`, `local_storage/`, `app/`). Syncing these causes corruption and merge storms. The ignore templates in `references/` already exclude them.

## Strategy A — Git (versioned, requires a private remote)
Use a **private** repository (GitHub private / GitLab / Gitee / self-hosted).

### Layer 1: Projects repo (`~/WorkBuddy`)
1. On the macOS machine, copy the ignore rules from `references/gitignore-projects.md` into `~/WorkBuddy/.gitignore`, and the `.gitattributes` block into `~/WorkBuddy/.gitattributes`.
2. Initialize and push:
   ```bash
   cd ~/WorkBuddy
   git init
   git remote add origin <PRIVATE_REMOTE_URL>
   git add .
   git commit -m "init: workbuddy projects"
   git push -u origin main
   ```
3. On the Windows machine (PowerShell), the base folder may already exist — back it up, clone, then merge local projects back in without overwriting:
   ```powershell
   # close WorkBuddy first
   cd ~
   Move-Item WorkBuddy WorkBuddy.old
   git clone <PRIVATE_REMOTE_URL> WorkBuddy
   robocopy WorkBuddy.old WorkBuddy /E /XC /XN /XO
   cd WorkBuddy
   git add .
   git commit -m "merge local projects"
   git push
   ```
4. Daily workflow on either OS — always pull before work, push after:
   - macOS (zsh): `cd ~/WorkBuddy && git pull --rebase && <work> && git add -A && git commit -m "update" && git push`
   - Windows (PowerShell): `cd ~\WorkBuddy; git pull --rebase; <work>; git add -A; git commit -m "update"; git push`

### Layer 2: Config repo (`~/.workbuddy`, optional but recommended)
Syncs memory, skills, and identity so the assistant "travels" with the user.
1. Copy `references/gitignore-config.md` rules into `~/.workbuddy/.gitignore` (macOS) / `%USERPROFILE%\.workbuddy\.gitignore` (Windows).
2. `git init` there, add remote, push (same steps as Layer 1 but in the config home).
3. **Review `settings.json` and `mcp.json`** before syncing: they may contain machine-specific absolute paths (MCP server command paths, plugin paths). If the two machines differ, move those two files from the "sync" list to the "ignore" list in the gitignore to avoid breaking config on the other machine.

## Strategy B — Syncthing (continuous two-way, handles binaries natively)
Prefer this when the user dislikes manual push/pull or has large generated media.
1. Install Syncthing on both machines; pair the devices.
2. Add the WorkBuddy base folder as a synced folder on each machine (use the verified paths from the Directory map).
3. Copy `references/stignore.md` content into a `.stignore` file at the folder root on both machines.
4. Let it sync continuously. No central repo, end-to-end encrypted.

## Gotchas checklist
- Close WorkBuddy fully before any clone/merge/restore operation on a machine.
- Use `git pull --rebase` to keep a linear history and avoid pointless merge commits.
- Cross-platform line endings: the `.gitattributes` with `* text=auto` (in `references/gitignore-projects.md`) prevents CRLF churn between macOS and Windows. Also run `git config --global core.autocrlf false` on the Windows machine.
- Project folders are timestamp-named, so two machines creating projects independently will not collide; conflicts only arise on shared text files (e.g. `MEMORY.md`) — resolve manually.
- Large media (videos/images) bloat git: either exclude them (default in the projects gitignore) or enable Git LFS. Syncthing handles them natively.
- Keep the remote **private**; the repos can contain personal files and config.

## Reconciliation if both machines diverged
1. Pick one machine as the source of truth.
2. On the other, `git stash` or `git checkout .` any local edits you don't need, then `git pull --rebase`.
3. If history already diverged badly, re-clone fresh (after backing up) and `robocopy /E /XC /XN /XO` local projects back in (Windows) or `cp -rn` (macOS).
