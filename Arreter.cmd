@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\local.ps1" -Action arreter
if errorlevel 1 pause
