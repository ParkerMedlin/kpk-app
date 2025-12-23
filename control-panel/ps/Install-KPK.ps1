<#
.SYNOPSIS
Installs the KPK PowerShell module and creates shortcuts.

.DESCRIPTION
Can be run from a network share or deployed via GPO.
Copies files to user's local modules folder and adds to PATH.

.EXAMPLE
# Install for current user
.\Install-KPK.ps1

# Install for all users (requires admin)
.\Install-KPK.ps1 -AllUsers

# Install from network share
\\server\share\kpk\Install-KPK.ps1

.PARAMETER AllUsers
Install to Program Files for all users (requires admin)

.PARAMETER SourcePath
Path to source files (defaults to script directory)

.PARAMETER SkipPathUpdate
Don't update PATH environment variable
#>

param(
    [switch]$AllUsers,
    [string]$SourcePath = $PSScriptRoot,
    [switch]$SkipPathUpdate
)

$ErrorActionPreference = 'Stop'

Write-Host "KPK Control Panel Installer" -ForegroundColor Cyan
Write-Host ""

# Determine install location
if ($AllUsers) {
    # Requires admin
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        throw "AllUsers install requires administrator privileges. Run as admin or omit -AllUsers."
    }
    $installDir = "C:\Program Files\KPK"
    $modulePath = "C:\Program Files\WindowsPowerShell\Modules\KPK"
} else {
    $installDir = Join-Path $env:LOCALAPPDATA "KPK"
    $modulePath = Join-Path (Join-Path $env:USERPROFILE "Documents\WindowsPowerShell\Modules") "KPK"
}

Write-Host "Install directory: $installDir"
Write-Host "Module path: $modulePath"
Write-Host ""

# Create directories
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    Write-Host "Created: $installDir" -ForegroundColor Green
}

$moduleParent = Split-Path $modulePath -Parent
if (-not (Test-Path $moduleParent)) {
    New-Item -ItemType Directory -Path $moduleParent -Force | Out-Null
}
if (-not (Test-Path $modulePath)) {
    New-Item -ItemType Directory -Path $modulePath -Force | Out-Null
    Write-Host "Created: $modulePath" -ForegroundColor Green
}

# Copy files
$filesToCopy = @("kpk.ps1", "kpk.cmd", "KPK.psm1")
foreach ($file in $filesToCopy) {
    $src = Join-Path $SourcePath $file
    if (Test-Path $src) {
        Copy-Item $src $installDir -Force
        Write-Host "Copied: $file -> $installDir" -ForegroundColor Green
    } else {
        Write-Warning "Source file not found: $src"
    }
}

# Copy module file to modules folder
$modSrc = Join-Path $SourcePath "KPK.psm1"
if (Test-Path $modSrc) {
    Copy-Item $modSrc $modulePath -Force
    Write-Host "Copied: KPK.psm1 -> $modulePath" -ForegroundColor Green
}

# Create module manifest
$manifestPath = Join-Path $modulePath "KPK.psd1"
$manifestContent = @"
@{
    RootModule = 'KPK.psm1'
    ModuleVersion = '1.0.0'
    GUID = '$(New-Guid)'
    Author = 'KPK Team'
    Description = 'KPK Control Panel - Manage Docker containers and host services'
    PowerShellVersion = '5.1'
    FunctionsToExport = @(
        'Set-KPKConfig',
        'Get-KPKConfig',
        'Invoke-KPKCommand',
        'Get-KPKStatus',
        'Start-KPKMissing',
        'Start-KPKAll',
        'Stop-KPKAll',
        'Get-KPKContainerList',
        'Get-KPKContainerLogs',
        'Start-KPKContainer',
        'Stop-KPKContainer',
        'Restart-KPKContainer',
        'Get-KPKHostServiceList',
        'Get-KPKHostServiceLogs',
        'Start-KPKHostService',
        'Stop-KPKHostService',
        'New-KPKBackup',
        'Get-KPKBackupList',
        'Restore-KPKBackup',
        'Get-KPKGitStatus',
        'Invoke-KPKGitFetch',
        'Invoke-KPKGitPull',
        'Invoke-KPKCollectStatic',
        'Invoke-KPKNginxReload'
    )
}
"@
Set-Content -Path $manifestPath -Value $manifestContent -Force
Write-Host "Created module manifest: $manifestPath" -ForegroundColor Green

# Update PATH
if (-not $SkipPathUpdate) {
    if ($AllUsers) {
        $scope = [EnvironmentVariableTarget]::Machine
    } else {
        $scope = [EnvironmentVariableTarget]::User
    }

    $currentPath = [Environment]::GetEnvironmentVariable("PATH", $scope)
    if ($currentPath -notlike "*$installDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$installDir", $scope)
        Write-Host "Added to PATH: $installDir" -ForegroundColor Green
        Write-Host "(Restart your terminal for PATH changes to take effect)" -ForegroundColor Yellow
    } else {
        Write-Host "PATH already contains: $installDir" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  # From command prompt (after restart):"
Write-Host "  kpk status"
Write-Host "  kpk container logs blue"
Write-Host ""
Write-Host "  # From PowerShell:"
Write-Host "  Import-Module KPK"
Write-Host "  Get-KPKStatus"
Write-Host ""
Write-Host "  # Or run directly:"
Write-Host "  & '$installDir\kpk.cmd' status"
