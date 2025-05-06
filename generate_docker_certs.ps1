param(
    [Parameter(Mandatory=$true)]
    [string]$ServerHostnameOrIP,

    [Parameter(Mandatory=$false)]
    [int]$CertValidityDays = 365,

    [Parameter(Mandatory=$false)]
    [int]$CAValidityDays = 1825, # 5 years

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ".\docker_certs"
)

# Check if OpenSSL is available
try {
    $opensslVersion = openssl version
    Write-Host "OpenSSL found: $opensslVersion"
}
catch {
    Write-Error "OpenSSL not found in PATH. Please install OpenSSL and ensure it's added to your system's PATH."
    exit 1
}

# Create output directories
$caDir = Join-Path -Path $OutputDir -ChildPath "ca"
$serverDir = Join-Path -Path $OutputDir -ChildPath "server"
$clientDir = Join-Path -Path $OutputDir -ChildPath "client"

New-Item -ItemType Directory -Path $caDir -Force | Out-Null
New-Item -ItemType Directory -Path $serverDir -Force | Out-Null
New-Item -ItemType Directory -Path $clientDir -Force | Out-Null

Write-Host "Generating certificates in $OutputDir"

# CA Certificate
Write-Host "Generating CA certificate..."
openssl genrsa -out (Join-Path $caDir "ca-key.pem") 4096
openssl req -new -x509 -days $CAValidityDays -key (Join-Path $caDir "ca-key.pem") -sha256 -out (Join-Path $caDir "ca.pem") -subj "/CN=MyDockerInternalCA" -nodes

# Server Certificate
Write-Host "Generating Server certificate for $ServerHostnameOrIP..."
openssl genrsa -out (Join-Path $serverDir "server-key.pem") 4096
openssl req -subj "/CN=$ServerHostnameOrIP" -sha256 -new -key (Join-Path $serverDir "server-key.pem") -out (Join-Path $serverDir "server.csr") -nodes

$serverExtFile = Join-Path $serverDir "extfile.cnf"
Set-Content -Path $serverExtFile -Value "subjectAltName = IP:$ServerHostnameOrIP,DNS:$ServerHostnameOrIP,DNS:localhost"
Add-Content -Path $serverExtFile -Value "extendedKeyUsage = serverAuth"

openssl x509 -req -days $CertValidityDays -sha256 -in (Join-Path $serverDir "server.csr") -CA (Join-Path $caDir "ca.pem") -CAkey (Join-Path $caDir "ca-key.pem") -CAcreateserial -out (Join-Path $serverDir "server-cert.pem") -extfile $serverExtFile

# Client Certificate
Write-Host "Generating Client certificate..."
openssl genrsa -out (Join-Path $clientDir "key.pem") 4096 # key.pem is the convention for client key in ~/.docker
openssl req -subj "/CN=client" -new -key (Join-Path $clientDir "key.pem") -out (Join-Path $clientDir "client.csr") -nodes

$clientExtFile = Join-Path $clientDir "extfile_client.cnf"
Set-Content -Path $clientExtFile -Value "extendedKeyUsage = clientAuth"
Add-Content -Path $clientExtFile -Value "subjectKeyIdentifier=hash"
Add-Content -Path $clientExtFile -Value "authorityKeyIdentifier=keyid,issuer"

openssl x509 -req -days $CertValidityDays -sha256 -in (Join-Path $clientDir "client.csr") -CA (Join-Path $caDir "ca.pem") -CAkey (Join-Path $caDir "ca-key.pem") -CAcreateserial -out (Join-Path $clientDir "cert.pem") -extfile $clientExtFile # cert.pem is convention for client cert

# Cleanup intermediate files
Remove-Item (Join-Path $serverDir "server.csr")
Remove-Item $serverExtFile
Remove-Item (Join-Path $clientDir "client.csr")
Remove-Item $clientExtFile
Remove-Item (Join-Path $caDir "ca.srl") # remove serial file, or manage it if CA is long-lived and reused often

Write-Host "---------------------------------------------------------------------"
Write-Host "Certificate generation complete!"
Write-Host "Files are located in $OutputDir"
Write-Host "  CA files: $caDir (ca.pem, ca-key.pem)"
Write-Host "  Server files: $serverDir (server-cert.pem, server-key.pem for Docker host $ServerHostnameOrIP)"
Write-Host "  Client files: $clientDir (cert.pem, key.pem, and ca.pem (copy from $caDir) for Docker clients)"
Write-Host "---------------------------------------------------------------------"
Write-Host "Next steps:"
Write-Host "1. On Docker Host ($ServerHostnameOrIP):"
Write-Host "   - Create directory C:\ProgramData\Docker\certs.d"
Write-Host "   - Copy '$caDir\ca.pem', '$serverDir\server-cert.pem', '$serverDir\server-key.pem' to C:\ProgramData\Docker\certs.d\"
Write-Host "   - Configure C:\ProgramData\Docker\config\daemon.json (see instructions)."
Write-Host "   - Restart Docker service."
Write-Host "   - Add firewall rule for TCP port 2376."
Write-Host "2. On Docker Client machines:"
Write-Host "   - Create directory %USERPROFILE%\.docker (if it doesn't exist)."
Write-Host "   - Copy '$clientDir\cert.pem', '$clientDir\key.pem', and '$caDir\ca.pem' to %USERPROFILE%\.docker\"
Write-Host "   - Set environment variables: DOCKER_HOST=tcp://$ServerHostnameOrIP:2376, DOCKER_TLS_VERIFY=1, DOCKER_CERT_PATH=%USERPROFILE%\.docker" 