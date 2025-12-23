@echo off
REM KPK Control Panel - Batch wrapper for PowerShell script
REM This avoids execution policy issues by using -ExecutionPolicy Bypass
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kpk.ps1" %*
