function Get-ConfigurationPath {
    # First, attempt the mapped drive
    $mappedPath = "\\Kinpak-Svr1\Apps\kpkapp\wol_config.json"
    $localPath = Join-Path $env:USERPROFILE "Documents\wol_config.json"
    
    # Test the mapped realm
    if (Test-Path "\\Kinpak-Svr1\Apps\kpkapp") {
        return @{
            Path = $mappedPath
            IsLocal = $false
        }
    } else {
        Write-Warning "Network path inaccessible. Falling back to local storage..."
        return @{
            Path = $localPath
            IsLocal = $true
        }
    }
}

function Get-WoLConfiguration {
    # Determine our sacred scroll's location
    $pathInfo = Get-ConfigurationPath
    
    # Commune with the network spirits
    $activeAdapter = Get-NetAdapter | 
        Where-Object { 
            $_.Status -eq 'Up' -and 
            $_.PhysicalMediaType -eq '802.3' 
        } |
        Select-Object Name, MacAddress -First 1
    
    if (-not $activeAdapter) {
        Write-Warning "No active Ethernet adapter found in the mortal realm!"
        return
    }
    
    # Get IP Address of the active adapter
    $ipAddress = Get-NetIPAddress -InterfaceAlias $activeAdapter.Name -AddressFamily IPv4 |
        Select-Object -ExpandProperty IPAddress
    
    # Prepare the ethereal configuration
    $configData = @{
        AdapterName = $activeAdapter.Name
        MacAddress = $activeAdapter.MacAddress
        IPAddress = $ipAddress
        LastUpdated = (Get-Date).ToString('o')
        StoragePath = $pathInfo.Path
        IsLocalStorage = $pathInfo.IsLocal
    }
    
    try {
        # Attempt to inscribe the knowledge
        $configData | ConvertTo-Json | Set-Content -Path $pathInfo.Path -ErrorAction Stop
        Write-Host "Configuration saved to: $($pathInfo.Path)" -ForegroundColor Green
    }
    catch {
        Write-Warning "Failed to write to primary location. Attempting local backup..."
        $localPath = Join-Path $env:USERPROFILE "Documents\wol_config.json"
        $configData.StoragePath = $localPath
        $configData.IsLocalStorage = $true
        $configData | ConvertTo-Json | Set-Content -Path $localPath
        Write-Host "Configuration saved to local backup: $localPath" -ForegroundColor Yellow
    }
    
    return $configData
}

# Test the connection's awakening capabilities
function Test-WoLCapability {
    $config = Get-WoLConfiguration
    
    if (-not $config) { return }
    
    $adapter = Get-NetAdapter | Where-Object Name -eq $config.AdapterName
    
    $wolStatus = @{
        AdapterName = $adapter.Name
        MacAddress = $adapter.MacAddress
        IPAddress = $config.IPAddress
        WolEnabled = $adapter.WolEnabled
        PowerManagementSupported = $adapter.PowerManagementSupported
        ConfigStoragePath = $config.StoragePath
        UsingLocalStorage = $config.IsLocalStorage
    }
    
    return $wolStatus
}

# Execute the primary ritual
$result = Get-WoLConfiguration
Write-Host "`nMAC Configuration details:" -ForegroundColor Cyan
$result | Format-List

# Test WoL readiness
$wolTest = Test-WoLCapability
Write-Host "`nWake-on-LAN Status:" -ForegroundColor Cyan
$wolTest | Format-List