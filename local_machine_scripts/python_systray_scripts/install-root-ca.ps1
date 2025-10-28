Param(
    [string]$CaPath = "$PSScriptRoot\..\..\nginx\ssl\kpkapp-rootCA.crt"
)

if (-not (Test-Path -Path $CaPath)) {
    Write-Error "Certificate file not found at '$CaPath'."
    exit 1
}

Write-Host "Importing root CA from $CaPath"

try {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CaPath)
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","LocalMachine")
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)

    $existing = $store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if ($existing) {
        Write-Host "Certificate already trusted (thumbprint $($cert.Thumbprint)). No action taken."
    }
    else {
        $store.Add($cert)
        Write-Host "Certificate installed to LocalMachine\Root."
    }

    $store.Close()
}
catch {
    Write-Error $_
    Write-Host "Try running PowerShell as Administrator."
    exit 1
}
