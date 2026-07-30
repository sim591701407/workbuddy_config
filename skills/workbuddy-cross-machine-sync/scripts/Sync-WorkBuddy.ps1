<#
.SYNOPSIS
    Daily WorkBuddy sync helper for Windows.

.DESCRIPTION
    Pulls remote changes and pushes local ones for both the config repo
    (%USERPROFILE%\.workbuddy) and the projects repo (%USERPROFILE%\WorkBuddy).

    Run with -Pull before starting work, and with no switch (or -Push)
    after finishing, so the other machine always sees the latest state.

.PARAMETER Pull
    Only pull. Use this when you sit down to work.

.PARAMETER Push
    Only commit and push. Use this when you finish.

.EXAMPLE
    .\Sync-WorkBuddy.ps1 -Pull

.EXAMPLE
    .\Sync-WorkBuddy.ps1
    # pull, then commit and push
#>

[CmdletBinding()]
param(
    [switch]$Pull,
    [switch]$Push,
    [string]$Message = "sync from $env:COMPUTERNAME"
)

$ErrorActionPreference = 'Continue'
$doPull = $Pull -or (-not $Pull -and -not $Push)
$doPush = $Push -or (-not $Pull -and -not $Push)

$repos = @(
    @{ Name = 'config';   Path = Join-Path $env:USERPROFILE '.workbuddy' },
    @{ Name = 'projects'; Path = Join-Path $env:USERPROFILE 'WorkBuddy'  }
)

foreach ($r in $repos) {
    Write-Host "`n==> $($r.Name)  ($($r.Path))" -ForegroundColor Cyan

    if (-not (Test-Path (Join-Path $r.Path '.git'))) {
        Write-Host "    [SKIP] not a git repository" -ForegroundColor Yellow
        continue
    }

    Push-Location $r.Path

    if ($doPull) {
        # Stash local edits so a rebase never aborts halfway.
        $dirty = (git status --porcelain)
        if ($dirty) { git stash push -u -m 'wb-autosync' | Out-Null }

        git pull --rebase
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    [FAIL] pull failed - resolve manually" -ForegroundColor Red
            Pop-Location
            continue
        }

        if ($dirty) {
            git stash pop
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    [WARN] stash pop hit a conflict - resolve, then re-run" -ForegroundColor Yellow
                Pop-Location
                continue
            }
        }
        Write-Host "    [OK] pulled" -ForegroundColor Green
    }

    if ($doPush) {
        if (git status --porcelain) {
            git add -A
            git commit -q -m $Message
            git push
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    [OK] pushed" -ForegroundColor Green
            } else {
                Write-Host "    [FAIL] push failed (auth? use a Personal Access Token as the password)" -ForegroundColor Red
            }
        } else {
            Write-Host "    [OK] nothing to commit" -ForegroundColor Green
        }
    }

    Pop-Location
}

Write-Host ''
