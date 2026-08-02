<#
    Open the board in a browser, with a Refresh button that runs the check
    on this machine.

        .\board.ps1              # serve on 8765 and open a browser
        .\board.ps1 -Port 9000   # somewhere else
        .\board.ps1 -NoOpen      # start the server, open it yourself

    The button runs run.ps1 — the same fetch, notify, pull-and-push as the
    terminal command. Leave this window open while you use the page; Ctrl+C
    stops the server. The scheduled cloud run is unaffected either way.

    The server listens on the loopback address only, so nothing outside this
    machine can reach it.
#>

[CmdletBinding()]
param(
    [int]$Port = 8765,
    [switch]$NoOpen
)

# Same reason as run.ps1: Python logs to stderr, and PowerShell 5.1 turns a
# native stderr line into a fatal error under "Stop".
$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

$serveArgs = @("-m", "src.serve", "--port", $Port)
if ($NoOpen) { $serveArgs += "--no-open" }

python @serveArgs
exit $LASTEXITCODE
