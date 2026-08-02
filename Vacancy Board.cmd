@echo off
rem Double-click this to open the board with its Refresh button.
rem
rem It starts the local server (board.ps1) and your browser. Keep this window
rem open while you use the page - closing it stops the server. Everything it
rem does is also available as .\board.ps1 from a terminal.

title Vacancy Board - keep this window open
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0board.ps1" %*

rem If it fell over immediately, hold the window open so the error is readable
rem rather than vanishing with the console.
if errorlevel 1 (
  echo.
  echo The server stopped with an error - see above.
  pause
)
