@echo off
rem ============================================================
rem  Stream server with mouse/keyboard control ENABLED.
rem  Run: double-click, or "stream_control" from cmd.
rem ============================================================
cd /d "%~dp0"

set STREAM_CONTROL=1
rem set STREAM_PASSWORD=1234

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" stream.py %*
) else (
    python stream.py %*
)
