<#
    Run the vacancy check from this machine.

    Why this exists: GitHub's runners are outside India and 9 of the 29
    sources refuse them, including both PESB feeds. A run from here reaches
    all 29, so this is the one that sees the whole picture.

        .\run.ps1                # full run: fetch, notify, push the board
        .\run.ps1 -DryRun        # print the message, send nothing, change nothing
        .\run.ps1 -CheckUrls     # just test every address in the config
        .\run.ps1 -NoPush        # run and notify, but leave git alone

    Credentials come from .env (see .env.example). The scheduled cloud run is
    unaffected by anything here.
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$CheckUrls,
    [switch]$NoPush
)

# Must stay "Continue": Python's logging writes to stderr, and under
# PowerShell 5.1 "Stop" turns any native stderr line into a fatal
# NativeCommandError. Failures are caught via exit codes below instead.
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot

# The board's signal aspects are emoji; cp1252 would abort on the first one.
$env:PYTHONIOENCODING = "utf-8"

if ($CheckUrls) {
    python -m src.main --check-urls
    exit $LASTEXITCODE
}

# --- get the cloud's state before writing our own -------------------------
# The scheduled run commits data/state.json too. Pulling first keeps the two
# from diverging into a conflict over the same file.
$dirty = $null
if (Test-Path ".git") {
    $dirty = git status --porcelain -- data/state.json docs
    if ($dirty) {
        Write-Host "Local board files already modified; skipping pull." -ForegroundColor Yellow
    }
    else {
        git pull --ff-only --quiet origin main
        if (-not $?) {
            Write-Host "Pull failed - resolve it before running, or use -NoPush." -ForegroundColor Red
            exit 1
        }
    }
}

# --- a dry run must leave no trace ----------------------------------------
# src/main.py saves state unconditionally, so a dry run would otherwise
# consume the "new" flags and the next real run would report nothing.
# The board files are rewritten too; leaving those modified would make the
# next run see a dirty tree, skip its pull, and risk diverging from the cloud.
$touched = @("data/state.json", "docs/index.html", "docs/vacancies.csv")
$backups = @{}
if ($DryRun) {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "vacancy-dryrun"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    foreach ($f in $touched) {
        if (Test-Path $f) {
            $dest = Join-Path $tmp (Split-Path $f -Leaf)
            Copy-Item $f $dest -Force
            $backups[$f] = $dest
        }
    }
}

try {
    if ($DryRun) { python -m src.main --dry-run } else { python -m src.main }
    $runExit = $LASTEXITCODE
}
finally {
    foreach ($f in $backups.Keys) {
        Copy-Item $backups[$f] $f -Force
    }
    if ($backups.Count -gt 0) {
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Dry run: state and board files restored." -ForegroundColor DarkGray
    }
}

if ($runExit -ne 0) {
    Write-Host "Run failed (exit $runExit); leaving git untouched." -ForegroundColor Red
    exit $runExit
}

if ($DryRun -or $NoPush) { exit 0 }

# --- publish, exactly as the workflow does --------------------------------
if (-not (Test-Path ".git")) { exit 0 }

git add data/state.json docs
git diff --staged --quiet
if ($LASTEXITCODE -ne 0) {
    git commit --quiet -m "Board update $(Get-Date -Format 'yyyy-MM-dd') (local run)"
    git push --quiet origin main
    if ($?) {
        Write-Host "Board pushed; the dashboard will rebuild shortly." -ForegroundColor Green
    }
    else {
        Write-Host "Commit made but push failed - push it manually." -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "Nothing changed on the board; nothing to push." -ForegroundColor DarkGray
}
