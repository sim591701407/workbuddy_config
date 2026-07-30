<#
.SYNOPSIS
    One-shot setup of WorkBuddy cross-machine sync on a Windows PC.

.DESCRIPTION
    Takes over the existing WorkBuddy folders in place, WITHOUT moving or
    deleting heavy runtime data (binaries/, plugins/, workbuddy.db ...).

    Strategy per repository:
      - Target folder missing        -> plain git clone
      - Target folder already a repo -> skip takeover, just report
      - Target folder exists (plain) -> back up the small text assets,
                                        clone with --no-checkout into a temp
                                        folder, move the .git directory in,
                                        then force-checkout main.

    Force-checkout only overwrites files that exist in the remote repo.
    Untracked local files (binaries, db, logs) are left untouched.

.PARAMETER ConfigRepo
    Git URL of the config repository (memory / skills / identity).
    Cloned into $env:USERPROFILE\.workbuddy

.PARAMETER ProjectsRepo
    Git URL of the projects repository.
    Cloned into $env:USERPROFILE\WorkBuddy

.PARAMETER SkipConfig
    Do not touch the config repository.

.PARAMETER SkipProjects
    Do not touch the projects repository.

.EXAMPLE
    .\Setup-WorkBuddySync.ps1

.EXAMPLE
    .\Setup-WorkBuddySync.ps1 -SkipProjects

.NOTES
    QUIT WORKBUDDY COMPLETELY BEFORE RUNNING THIS SCRIPT.
#>

[CmdletBinding()]
param(
    [string]$ConfigRepo   = 'https://github.com/sim591701407/workbuddy_config.git',
    [string]$ProjectsRepo = 'https://github.com/sim591701407/workbuddy_xm.git',
    [switch]$SkipConfig,
    [switch]$SkipProjects
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

function Write-Step { param($m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    [OK]   $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    [WARN] $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "    [FAIL] $m" -ForegroundColor Red }

# ---------------------------------------------------------------- preflight
Write-Step 'Preflight checks'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Err 'git is not installed or not on PATH. Install Git for Windows first: https://git-scm.com/download/win'
    exit 1
}
Write-Ok  ("git found: " + (git --version))

$running = Get-Process -Name 'WorkBuddy*' -ErrorAction SilentlyContinue
if ($running) {
    Write-Err 'WorkBuddy is still running. Quit it completely (check the tray icon), then re-run this script.'
    exit 1
}
Write-Ok 'WorkBuddy is not running'

# Long path support avoids checkout failures on deep node_modules paths.
git config --global core.longpaths true
Write-Ok 'core.longpaths enabled'

# ----------------------------------------------------------------- takeover
function Invoke-Takeover {
    param(
        [string]$Path,
        [string]$RepoUrl,
        [string]$Label,
        [string[]]$BackupItems
    )

    Write-Step "$Label  ->  $Path"

    # Case 1: folder does not exist -> plain clone
    if (-not (Test-Path $Path)) {
        Write-Host "    Folder not found, cloning fresh..."
        git clone $RepoUrl $Path
        if ($LASTEXITCODE -ne 0) { Write-Err "clone failed for $Label"; return }
        Push-Location $Path
        git config core.autocrlf false
        Pop-Location
        Write-Ok "$Label cloned"
        return
    }

    # Case 2: already a git repo -> nothing to take over
    if (Test-Path (Join-Path $Path '.git')) {
        Write-Warn "$Path is already a git repository. Skipping takeover."
        Push-Location $Path
        $existing = (git remote get-url origin 2>$null)
        Write-Host "    existing origin: $existing"
        Write-Host "    To sync manually:  cd `"$Path`" ; git pull --rebase"
        Pop-Location
        return
    }

    # Case 3: plain folder with local data -> back up, then graft .git in
    $backupDir = "$Path.backup-$stamp"
    Write-Host "    Backing up text assets to: $backupDir"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    foreach ($item in $BackupItems) {
        $src = Join-Path $Path $item
        if (Test-Path $src) {
            Copy-Item $src -Destination $backupDir -Recurse -Force
        }
    }
    Write-Ok 'Backup done'

    $temp = Join-Path $env:TEMP "wbsync-$stamp-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    Write-Host '    Cloning metadata (--no-checkout)...'
    git clone --no-checkout $RepoUrl $temp
    if ($LASTEXITCODE -ne 0) {
        Write-Err "clone failed for $Label. Backup kept at $backupDir"
        return
    }

    Move-Item (Join-Path $temp '.git') (Join-Path $Path '.git') -Force
    Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue

    Push-Location $Path
    git config core.autocrlf false
    Write-Host '    Checking out main (overwrites tracked files only)...'
    git checkout -f main
    if ($LASTEXITCODE -ne 0) {
        Write-Err "checkout failed. Your data is intact; backup at $backupDir"
        Pop-Location
        return
    }
    git branch --set-upstream-to=origin/main main 2>$null | Out-Null
    Pop-Location

    Write-Ok "$Label is now tracking origin/main"
    Write-Warn "Backup kept at $backupDir  (delete it once you verified everything)"
}

# -------------------------------------------------------------------- run
if (-not $SkipConfig) {
    Invoke-Takeover `
        -Path        (Join-Path $env:USERPROFILE '.workbuddy') `
        -RepoUrl     $ConfigRepo `
        -Label       'Config repo (memory / skills / identity)' `
        -BackupItems @('memory', 'skills', 'SOUL.md', 'IDENTITY.md', 'USER.md', 'MEMORY.md')
}

if (-not $SkipProjects) {
    Invoke-Takeover `
        -Path        (Join-Path $env:USERPROFILE 'WorkBuddy') `
        -RepoUrl     $ProjectsRepo `
        -Label       'Projects repo' `
        -BackupItems @('.gitignore')
}

# ------------------------------------------------------------------ finish
Write-Step 'Done'
Write-Host @"
    Daily sync on this PC (run BEFORE and AFTER a work session):

      cd `$env:USERPROFILE\.workbuddy ; git pull --rebase ; git add -A ; git commit -m "update" ; git push
      cd `$env:USERPROFILE\WorkBuddy  ; git pull --rebase ; git add -A ; git commit -m "update" ; git push

    Authentication: GitHub no longer accepts account passwords.
    When prompted for a password, paste a Personal Access Token instead.

    Now relaunch WorkBuddy and confirm your memory and skills are present.
"@ -ForegroundColor Gray
