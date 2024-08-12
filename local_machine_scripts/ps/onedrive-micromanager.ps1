$maxRetries = 3
$retryDelay = 30
$oneDrivePath = "C:\Program Files\Microsoft OneDrive\OneDrive.exe"
$logName = "Application"
$source = "OneDriveWatchdog"
$mutexName = "Global\OneDriveWatchdogMutex"

# SMTP settings
$smtpServer = "smtp.office365.com"
$port = 587
$from = "pmedlin@kinpakinc.com"
$to = @("jdavis@kinpakinc.com", "pmedlin@kinpakinc.com")

# Create the event source if it doesn't exist
if (-not [System.Diagnostics.EventLog]::SourceExists($source)) {
    [System.Diagnostics.EventLog]::CreateEventSource($source, $logName)
}

# Create or open the mutex
$mutex = New-Object System.Threading.Mutex($false, $mutexName)
$hasHandle = $false

try {
    # Try to acquire the mutex
    $hasHandle = $mutex.WaitOne(0, $false)
    if (-not $hasHandle) {
        Write-Output "Another instance of the script is already running."
        exit 0
    }

    function Close-OneDriveExplorerWindow {
        Write-Output "Attempting to close OneDrive Explorer window..."
        $explorerProcesses = Get-Process explorer -ErrorAction SilentlyContinue
        foreach ($process in $explorerProcesses) {
            if ($process.MainWindowTitle -eq "Parker - Kinpak, Inc") {
                $process.CloseMainWindow() | Out-Null
                Start-Sleep -Seconds 1
                if (!$process.HasExited) {
                    $process | Stop-Process -Force
                }
                Write-Output "OneDrive Explorer window closed."
            }
        }
    }

    function Restart-OneDrive {
        Write-Output "Attempting to restart OneDrive..."
        Get-Process OneDrive -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 5
        if (Test-Path $oneDrivePath) {
            Start-Process $oneDrivePath
            Start-Sleep -Seconds 10
            Close-OneDriveExplorerWindow
            Write-Output "OneDrive restarted successfully."
        } else {
            throw "OneDrive executable not found at $oneDrivePath"
        }
    }

    function Send-AlertEmail {
        param($body)
        $computerName = $env:COMPUTERNAME
        $subject = "OneDrive Failure on $computerName"
        
        # Pull creds from WCM
        Write-Output "Retrieving credentials from WCM..."
        $credentialData = cmdkey /generic:OneDriveWatchdogSMTP /user:pmedlin@kinpakinc.com /pass
        $username = ($credentialData | Select-String 'User:').ToString().Split(':')[1].Trim()
        $password = ($credentialData | Select-String 'Password:').ToString().Split(':')[1].Trim() | ConvertTo-SecureString -AsPlainText -Force
        $cred = New-Object System.Management.Automation.PSCredential($username, $password)

        try {
            Write-Output "Sending alert email..."
            Send-MailMessage -From $from -To $to -Subject $subject -Body $body -SmtpServer $smtpServer -Port $port -UseSsl -Credential $cred -ErrorAction Stop
            Write-EventLog -LogName $logName -Source $source -EventId 1002 -EntryType Information -Message "Alert email sent successfully."
            Write-Output "Alert email sent successfully."
        }
        catch {
            Write-EventLog -LogName $logName -Source $source -EventId 1003 -EntryType Error -Message "Failed to send alert email: $_"
            Write-Output "Failed to send alert email: $_"
        }
    }

    for ($i = 0; $i -lt $maxRetries; $i++) {
        Write-Output "Checking OneDrive status (Attempt $($i + 1) of $maxRetries)..."
        $oneDriveProcess = Get-Process OneDrive -ErrorAction SilentlyContinue
        if ($oneDriveProcess -and $oneDriveProcess.Responding) {
            $message = "OneDrive is running and responsive."
            Write-EventLog -LogName $logName -Source $source -EventId 1000 -EntryType Information -Message $message
            Write-Output $message
             try {
                Restart-OneDrive
            } catch {
                $errorMessage = "Failed to restart OneDrive: $_"
                Write-EventLog -LogName $logName -Source $source -EventId 1001 -EntryType Error -Message $errorMessage
                Write-Output $errorMessage
                Send-AlertEmail -body $errorMessage
                exit 1
            }
            exit 0
        } else {
            try {
                Restart-OneDrive
            } catch {
                $errorMessage = "Failed to restart OneDrive: $_"
                Write-EventLog -LogName $logName -Source $source -EventId 1001 -EntryType Error -Message $errorMessage
                Write-Output $errorMessage
                Send-AlertEmail -body $errorMessage
                exit 1
            }
        }
        Start-Sleep -Seconds $retryDelay
    }

    $failureMessage = "OneDrive failed to start or respond after $maxRetries attempts."
    Write-EventLog -LogName $logName -Source $source -EventId 1001 -EntryType Error -Message $failureMessage
    Write-Output $failureMessage
    Send-AlertEmail -body $failureMessage
    exit 1
} finally {
    if ($hasHandle) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}