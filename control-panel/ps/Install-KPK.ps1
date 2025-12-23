<#
.SYNOPSIS
Installs the KPK PowerShell CLI by adding a function to user's PowerShell profile.

.DESCRIPTION
Sets up a 'kpk' function in your PowerShell profile that runs the PowerShell CLI.
Works with both Windows PowerShell and PowerShell 7.
Handles OneDrive Documents folder redirection automatically.

.EXAMPLE
# Install for current user
.\Install-KPK.ps1

# Uninstall
.\Install-KPK.ps1 -Uninstall

.PARAMETER SourcePath
Path to kpk.ps1 (defaults to script directory)

.PARAMETER Uninstall
Remove the kpk function from PowerShell profiles
#>

param(
    [string]$SourcePath = $PSScriptRoot,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

Write-Host "KPK Control Panel Installer" -ForegroundColor Cyan
Write-Host ""

# Get actual Documents folder (handles OneDrive redirect)
$documentsPath = [Environment]::GetFolderPath('MyDocuments')
Write-Host "Documents folder: $documentsPath"

# Profile locations for both PowerShell versions
$profiles = @(
    @{
        Name = "Windows PowerShell"
        Path = Join-Path $documentsPath "WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
    },
    @{
        Name = "PowerShell 7"
        Path = Join-Path $documentsPath "PowerShell\Microsoft.PowerShell_profile.ps1"
    }
)

# Path to kpk.ps1 script
$kpkScript = Join-Path $SourcePath "kpk.ps1"
if (-not (Test-Path $kpkScript)) {
    throw "kpk.ps1 not found at: $kpkScript"
}
$kpkScriptPath = (Resolve-Path $kpkScript).Path

# The function block we add to profiles
$functionBlock = @"

# KPK Control Panel CLI (auto-updates from source)
function kpk {
    & "$kpkScriptPath" @args
}
"@

$markerStart = "# KPK Control Panel CLI"

if ($Uninstall) {
    Write-Host "Uninstalling..." -ForegroundColor Yellow
    foreach ($profile in $profiles) {
        if (Test-Path $profile.Path) {
            $content = Get-Content $profile.Path -Raw
            if ($content -match [regex]::Escape($markerStart)) {
                # Remove the function block
                $pattern = "(?s)\r?\n?# KPK Control Panel CLI.*?function kpk \{.*?\}"
                $newContent = $content -replace $pattern, ""
                Set-Content -Path $profile.Path -Value $newContent.TrimEnd() -NoNewline
                Write-Host "Removed from: $($profile.Name)" -ForegroundColor Green
            }
        }
    }
    Write-Host ""
    Write-Host "Uninstall complete. Restart your terminal." -ForegroundColor Green
    return
}

# Install to each profile
foreach ($profile in $profiles) {
    $profileDir = Split-Path $profile.Path -Parent

    # Create directory if needed
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
        Write-Host "Created: $profileDir" -ForegroundColor Green
    }

    # Read or initialize profile content
    if (Test-Path $profile.Path) {
        $content = Get-Content $profile.Path -Raw
        if ([string]::IsNullOrEmpty($content)) {
            $content = ""
        }
    } else {
        $content = ""
    }

    # Check if already installed
    if ($content -match [regex]::Escape($markerStart)) {
        # Update existing - replace the function block
        $pattern = "(?s)# KPK Control Panel CLI.*?function kpk \{.*?\}"
        $replacement = $functionBlock.TrimStart()
        $newContent = $content -replace $pattern, $replacement
        Set-Content -Path $profile.Path -Value $newContent -NoNewline
        Write-Host "Updated: $($profile.Name)" -ForegroundColor Green
    } else {
        # Add new
        $newContent = $content.TrimEnd() + "`n" + $functionBlock
        Set-Content -Path $profile.Path -Value $newContent -NoNewline
        Write-Host "Added to: $($profile.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Restart your terminal, then use:" -ForegroundColor Yellow
Write-Host "  kpk status"
Write-Host "  kpk container logs blue"
Write-Host "  kpk host start data_sync"
Write-Host ""
Write-Host "The 'kpk' command runs directly from source - no reinstall needed after updates." -ForegroundColor Cyan
