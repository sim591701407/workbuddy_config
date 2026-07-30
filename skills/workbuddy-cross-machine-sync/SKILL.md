---
name: workbuddy-cross-machine-sync
description: Set up and maintain cross-machine synchronization of WorkBuddy projects and user config (memory, skills, settings) between a macOS and a Windows PC using git or Syncthing. This skill should be used when the user wants to sync WorkBuddy data across two or more computers, asks how to keep projects consistent between a Mac and a Windows machine, needs git-based or peer-to-peer sync instructions for WorkBuddy, or hits git auth/push failures while doing so.
agent_created: true
---

# WorkBuddy 跨设备同步（macOS ↔ Windows）

## Purpose
Synchronize a user's WorkBuddy workspace across two computers (one macOS, one Windows) so that projects, artifacts, memory, and skills stay consistent. Two strategies: (1) git-based versioned sync via a private remote, (2) Syncthing peer-to-peer continuous sync.

## When to use
- "How do I sync WorkBuddy between my Mac and Windows PC?" / "keep projects consistent across computers".
- User wants assistant memory/skills to follow them to another machine.
- User reports drift between machines and needs reconciliation.
- User hits `Invalid username or token`, `502 CONNECT tunnel failed`, or an empty remote repo while setting this up.

## Directory map (verify before acting)
| Scope | macOS | Windows |
|-------|-------|---------|
| Projects base | `~/WorkBuddy` | `%USERPROFILE%\WorkBuddy` |
| Config home | `~/.workbuddy` | `%USERPROFILE%\.workbuddy` |

Confirm the actual Windows path before cloning — the base folder name can differ.

## Critical rules (never violate)

**1. Never sync runtime state.** `workbuddy.db` (+ `-shm`/`-wal`), `logs/`, `sessions/`, `binaries/`, `blobs/`, `file-history/`, `traces/`, `shell-snapshots/`, `local_storage/`, `app/`, `plugins/`, `connectors/`. SQLite over git = corruption and merge storms. The templates in `references/` already exclude these.

**2. Config repo uses a whitelist gitignore.** `~/.workbuddy` holds tokens and machine-specific paths. Ignore everything by default (`/*`), then explicitly un-ignore `memory/`, `skills/`, `SOUL.md`, `IDENTITY.md`, `USER.md`. Never `git add .` there without reviewing `git status --short` first.

**3. ALWAYS check for a parent git repo before `git init`.** Run this first:
```bash
cd ~/WorkBuddy && git rev-parse --show-toplevel
```
If it prints a path *above* the target (e.g. `/Users/<user>`), the home directory is itself a repo — a real, observed situation (a stale GitHub Pages repo from years earlier, remote pointing at a **public** `<user>.github.io`). Consequences: a stray `git add -A && git push` in `~` would publish the entire home directory, including SSH keys and `.workbuddy`. Running `git init` inside `~/WorkBuddy` creates a nested repo whose `.git` shadows the parent, which fixes the WorkBuddy side. Also warn the user about the parent repo itself, and verify with `git ls-files | head` whether anything sensitive is already tracked.

## Automated path (preferred)

`scripts/` contains ready-to-run helpers. Adjust the default repo URLs at the top of the PowerShell scripts, or pass them as parameters.

| Script | Platform | Purpose |
|--------|----------|---------|
| `Setup-WorkBuddySync.ps1` | Windows | One-shot takeover of an existing WorkBuddy install |
| `Sync-WorkBuddy.ps1` | Windows | Daily pull / commit / push for both repos |
| `wb-sync.sh` | macOS | Daily pull / commit / push for both repos |

**Setup-WorkBuddySync.ps1 design (why it is safe):** it does *not* move the existing folder. It backs up the small text assets, runs `git clone --no-checkout` into `%TEMP%`, moves the resulting `.git` into the target folder, then `git checkout -f main`. Force-checkout only overwrites files that exist in the remote; untracked local data (binaries, db, logs) is left in place. It refuses to run while WorkBuddy is open and enables `core.longpaths`.

```powershell
# Windows, after quitting WorkBuddy:
.\Setup-WorkBuddySync.ps1
.\Setup-WorkBuddySync.ps1 -SkipProjects     # config repo only
```

```bash
# macOS one-time install of the daily helper:
chmod +x ~/.workbuddy/skills/workbuddy-cross-machine-sync/scripts/wb-sync.sh
ln -sf ~/.workbuddy/skills/workbuddy-cross-machine-sync/scripts/wb-sync.sh /usr/local/bin/wb-sync
wb-sync pull    # before working
wb-sync push    # after working
```

## Manual path — Strategy A: Git

Use two **private** repos (projects and config kept separate, so large project files never bloat the config repo).

### Layer 1: Projects repo (`~/WorkBuddy`)
1. Copy ignore rules from `references/gitignore-projects.md` into `~/WorkBuddy/.gitignore` and the `.gitattributes` block into `~/WorkBuddy/.gitattributes`.
2. Check for a parent repo (Critical rule 3), then:
   ```bash
   cd ~/WorkBuddy
   git init && git add -A
   git status --short          # review before committing
   git commit -m "init: workbuddy projects"
   git branch -M main
   git remote add origin <PRIVATE_REMOTE_URL>
   git push -u origin main
   ```
3. Windows side: run `Setup-WorkBuddySync.ps1`, or do it manually with the clone/robocopy dance.

### Layer 2: Config repo (`~/.workbuddy`)
Same flow, but with the whitelist gitignore from `references/gitignore-config.md`. Expect roughly a handful of files. Verify with `git status --short` that no `.db`, `settings.json`, `mcp.json`, or `connectors/` appear.

`settings.json` / `mcp.json` are excluded by default — they often carry machine-specific absolute paths and secrets. Only add them if the user confirms both machines are identical and the files are clean.

## Authentication (a guaranteed stumbling block)

**GitHub removed password authentication for git in 2021.** When the terminal prompts for a password and the user types their GitHub account password, it fails with:
```
remote: Invalid username or token. Password authentication is not supported for Git operations.
```

Fix — paste a **Personal Access Token** into the password field:
1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
2. **Repository access** → *Only select repositories* → pick just the target repo.
3. The **Contents** permission lives in the **Repositories** tab (not the Account tab). Use `+ Add permissions` → `Contents` → **Read and write**. `Metadata: Read-only` is mandatory and added automatically.
4. On macOS run `git config --global credential.helper osxkeychain` once, then push and paste the token as the password — it is cached afterwards.

### `The requested URL returned error: 403` on the *second* repo

Observed right after the first repo pushed fine. Two causes, usually both at once:

1. **Fine-grained tokens are repo-scoped.** A token generated with *Only select repositories → repo A* returns **403 on repo B**. Either edit the existing token to select both repos, or generate a second one. (403 = authenticated but not authorized; 404 on a private repo means the token cannot even see it — same root cause.)
2. **macOS keychain silently replays the stale token.** `credential.helper = osxkeychain` is often preset in `/usr/local/etc/gitconfig` (Homebrew git), so git reuses the cached entry and never prompts — the user sees only 403. Purge it before retrying:
   ```bash
   printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain erase
   ```
   Inspect what is cached with `security find-internet-password -s github.com`. A stale `acct` (e.g. an old email from the password era) is a strong tell.

Then `git push -u origin main` again → username = GitHub *login name* (not the email), password = the new token.

Also verify the remote URL matches the repo the user actually created (`git remote -v`); a renamed repo produces the same 403/404.

SSH is the friction-free alternative and sidesteps all per-repo token scoping: `ssh-keygen -t ed25519`, add the public key to GitHub, then `git remote set-url origin git@github.com:<user>/<repo>.git`.

**Never push from the assistant's sandbox.** The sandbox has no GitHub credentials, has interactive prompts disabled, and its proxy intermittently returns `502 CONNECT tunnel failed`. Prepare the commit locally, then hand the user a single command to run in *their own* terminal. Also note the sandbox may be a read-only mirror of the user's filesystem — after the user pushes, the sandbox may still show no upstream tracking. Verify against the actual remote (ask the user), not the sandbox's `git branch -vv`.

**"Push looked fine but the repo is empty"** almost always means an earlier attempt failed silently while a later one succeeded, or the user checked before the successful push. A genuine success prints `* [new branch] main -> main`.

## Strategy B — Syncthing (continuous two-way)
Prefer when the user dislikes manual push/pull or has large generated media.
1. Install on both machines and pair the devices.
2. Add the WorkBuddy base folder as a synced folder on each.
3. Copy `references/stignore.md` into `.stignore` at the folder root on both machines.
4. No central repo, end-to-end encrypted, handles binaries natively — but no version history.

## Gotchas checklist
- Quit WorkBuddy fully before any clone/merge/restore.
- `git pull --rebase` keeps history linear.
- Line endings: `.gitattributes` with `* text=auto`, plus `git config --global core.autocrlf false` on Windows.
- Enable `core.longpaths true` on Windows or deep paths fail on checkout.
- Project folders are timestamp-named, so independent creations never collide; conflicts only hit shared text files like `MEMORY.md`.
- Videos/archives bloat git — excluded by default. Images are kept (they are usually deliverables).
- Keep both remotes **private**.
- Do not write `.ps1`/`.bat` files containing non-ASCII text for Windows — PowerShell 5.1 mangles UTF-8 without BOM. Keep script output in English.

## Reconciliation if both machines diverged
1. Pick one machine as source of truth.
2. On the other: `git stash` (or discard) local edits, then `git pull --rebase`.
3. If history diverged badly: back up, re-clone fresh, then merge local-only files back with `robocopy <old> <new> /E /XC /XN /XO` (Windows) or `cp -rn` (macOS).
