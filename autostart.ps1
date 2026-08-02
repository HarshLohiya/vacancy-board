<#
    Have the board's local server start whenever you log in, so the Refresh
    button on the page is always live and there is nothing to launch.

        .\autostart.ps1 -Install    # start it at every logon, and now
        .\autostart.ps1 -Remove     # stop doing that
        .\autostart.ps1 -Status     # is it set up, is it running

    It puts a shortcut in your own Startup folder — no admin rights, no
    scheduled task, no service. Removing it is deleting that one file, which
    -Remove does for you.

    The server runs under pythonw.exe, which has no console, so nothing
    appears on screen at logon and nothing appears while a run is going. It
    listens on 127.0.0.1 only.

    If the button ever stops appearing on the page, run .\board.ps1 from a
    terminal: it does the same thing with the errors visible.
#>

[CmdletBinding(DefaultParameterSetName = "Status")]
param(
    [Parameter(ParameterSetName = "Install")][switch]$Install,
    [Parameter(ParameterSetName = "Remove")][switch]$Remove,
    [Parameter(ParameterSetName = "Status")][switch]$Status,
    [int]$Port = 8765
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot

$startup = [Environment]::GetFolderPath("Startup")
$link = Join-Path $startup "Vacancy Board server.lnk"

function Get-Pythonw {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { return $null }
    # pythonw is the same interpreter without a console window; it sits
    # beside python.exe in every standard install.
    $pyw = Join-Path (Split-Path $py -Parent) "pythonw.exe"
    if (Test-Path $pyw) { return $pyw }
    return $py
}

function Test-Serving {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:$Port/api/status" `
             -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    }
    catch { return $false }
}

if ($Install) {
    $pyw = Get-Pythonw
    if (-not $pyw) {
        Write-Host "Python is not on PATH - install it, or use .\board.ps1." -ForegroundColor Red
        exit 1
    }

    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($link)
    $sc.TargetPath = $pyw
    $sc.Arguments = "-m src.serve --port $Port --no-open"
    $sc.WorkingDirectory = $PSScriptRoot
    $sc.Description = "Serves the vacancy board on 127.0.0.1:$Port with its Refresh button"
    $sc.WindowStyle = 7   # minimised, for the case where a console does exist
    $sc.Save()

    Write-Host "Installed: $link" -ForegroundColor Green

    # Start it now as well, so you do not have to log out to use it.
    if (Test-Serving) {
        Write-Host "Already serving on port $Port." -ForegroundColor DarkGray
    }
    else {
        Start-Process -FilePath $pyw `
            -ArgumentList "-m", "src.serve", "--port", $Port, "--no-open" `
            -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
        Start-Sleep -Seconds 2
        if (Test-Serving) {
            Write-Host "Started. The board is at http://127.0.0.1:$Port/" -ForegroundColor Green
            Write-Host "Bookmark that - the Refresh button is on it." -ForegroundColor Green
        }
        else {
            Write-Host "Could not start it. Run .\board.ps1 to see why." -ForegroundColor Red
            exit 1
        }
    }
    exit 0
}

if ($Remove) {
    if (Test-Path $link) {
        Remove-Item $link -Force
        Write-Host "Removed: $link" -ForegroundColor Green
    }
    else {
        Write-Host "Nothing installed." -ForegroundColor DarkGray
    }
    Write-Host "A server already running stays up until you log out or stop" -ForegroundColor DarkGray
    Write-Host "pythonw.exe in Task Manager." -ForegroundColor DarkGray
    exit 0
}

# --- default: report -------------------------------------------------------
if (Test-Path $link) {
    Write-Host "Starts at logon: yes  ($link)"
}
else {
    Write-Host "Starts at logon: no   (.\autostart.ps1 -Install)"
}
if (Test-Serving) {
    Write-Host "Serving now:     yes  http://127.0.0.1:$Port/"
}
else {
    Write-Host "Serving now:     no"
}
