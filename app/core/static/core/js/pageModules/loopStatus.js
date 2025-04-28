$(document).ready(function() {
    // Function to apply row coloring based on timestamp age
    function applyRowColoring() {
        const now = new Date();
        $('tbody tr').each(function() {
            const tsText = $(this).find('td:nth-child(2)').text();
            const ts = new Date(tsText);
            if ((now - ts) / (1000 * 60) > 6) {
                $(this).removeClass().addClass('failure');
            } else {
                $(this).removeClass().addClass('success');
            }
        });
    }

    // Function to sort table rows by Last Run ascending
    function sortTableAsc() {
        const rows = $('tbody tr').get();
        rows.sort((a, b) => {
            const dateA = new Date($(a).find('td:nth-child(2)').text());
            const dateB = new Date($(b).find('td:nth-child(2)').text());
            return dateA - dateB;
        });
        $.each(rows, (_idx, row) => $('tbody').append(row));
    }

    // Initial sorting and coloring
    sortTableAsc();
    applyRowColoring();

    // --- Log Console Elements --- 
    const $logWindow = $('#logConsoleWindow');
    const $logOutput = $('#logConsoleOutput');
    const $logStatus = $('#logConsoleStatus');
    const $closeLogBtn = $('#closeLogBtn');
    const $refreshLogBtn = $('#refreshLogBtn');
    const $copyLogBtn = $('#copyLogBtn');
    const $restartLoopBtn = $('#restartLoopBtn'); // Main restart button

    // --- Log Polling State --- 
    let logPollingInterval = null; 
    let currentLogOffset = 0;
    const pollingRateMs = 1000; // Poll every 1 second (adjust as needed)
    const logUrl = '/core/get-data-looper-log/'; // URL for fetching logs
    const triggerUrl = '/core/trigger-restart/'; // URL to trigger the restart

    // --- Function to Fetch Log Updates --- 
    function fetchLogUpdates() {
        $.ajax({
            url: logUrl,
            type: 'GET',
            data: { offset: currentLogOffset },
            dataType: 'json',
            timeout: 5000, // Short timeout for polling
            success: function(response) {
                if (response.logs) {
                    // Append new logs, maintain scroll position if not at bottom
                    const shouldScroll = $logOutput.scrollTop() + $logOutput.innerHeight() >= $logOutput[0].scrollHeight - 20; // Tolerance
                    $logOutput.append(document.createTextNode(response.logs)); // Use createTextNode for safety
                    if (shouldScroll) {
                        $logOutput.scrollTop($logOutput[0].scrollHeight);
                    }
                }
                currentLogOffset = response.new_offset;
                
                // Handle specific error statuses from backend if needed
                if (response.error) {
                    $logStatus.text(`Status: ${response.status || 'Error polling'}. Retrying...`);
                    // Optionally stop polling on certain errors:
                    // if (response.status === 'not_found' || response.status === 'disappeared') {
                    //     stopLogPolling('Log file not found or inaccessible.');
                    //     return; // Stop trying
                    // }
                } else {
                    $logStatus.text('Status: Monitoring...');
                }

                // Schedule next poll if polling is active
                if (logPollingInterval !== null) {
                   logPollingInterval = setTimeout(fetchLogUpdates, pollingRateMs); 
                }
            },
            error: function(xhr, status, error) {
                console.error(`AJAX error polling logs: Status: ${status}, Error: ${error}`);
                $logStatus.text(`Status: Error connecting (${status}). Retrying...`);
                // Schedule next poll even on error (might be temporary network issue)
                if (logPollingInterval !== null) {
                    logPollingInterval = setTimeout(fetchLogUpdates, pollingRateMs * 2); // Retry less frequently on error
                }
            }
        });
    }

    // --- Function to Start Log Polling --- 
    function startLogPolling(showConsole = true) {
        stopLogPolling(); // Clear any existing interval
        currentLogOffset = 0; // Reset offset
        $logOutput.empty(); // Clear previous logs
        $logStatus.text('Status: Connecting...');
        if (showConsole) {
             $logWindow.fadeIn(); // Show the console window
        }
        // Start the first poll immediately, then schedule subsequent ones
        logPollingInterval = setTimeout(fetchLogUpdates, 100); // Start quickly
        console.log("Log polling started.");
    }

    // --- Function to Stop Log Polling --- 
    function stopLogPolling(finalStatus = 'Monitoring stopped.') {
        if (logPollingInterval) {
            clearTimeout(logPollingInterval);
            logPollingInterval = null;
            $logStatus.text(`Status: ${finalStatus}`);
            console.log("Log polling stopped.");
        }
    }

    // --- Event Listener for Restart Button --- 
    $restartLoopBtn.on('click', function() {
        const $btn = $(this);
        // Only disable briefly, main status in console now
        $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-2"></i> Triggering...');

        // 1. Start showing logs *before* triggering
        startLogPolling(); 

        // 2. Trigger the restart via the backend
        $.ajax({
            url: triggerUrl,
            type: 'GET',
            dataType: 'json',
            timeout: 10000, 
            success: function(response) {
                // The backend trigger endpoint might just confirm the trigger request was sent
                if (response.status === 'success') {
                    console.log("Django backend reported trigger success:", response.message);
                     $logOutput.append(document.createTextNode('[INFO] Restart command successfully sent to host service.\n'));
                     $logOutput.scrollTop($logOutput[0].scrollHeight); // Scroll down
                    // Button resets relatively quickly
                    $btn.html('<i class="fas fa-check mr-2"></i> Triggered');
                } else {
                    console.error("Django backend reported trigger error:", response.message);
                    $logOutput.append(document.createTextNode(`[ERROR] Failed to send restart command: ${response.message}\n`));
                    $logOutput.scrollTop($logOutput[0].scrollHeight); // Scroll down
                    stopLogPolling('Failed to trigger restart.');
                    // Indicate failure on button too
                     $btn.removeClass("btn-warning").addClass("btn-danger")
                        .html('<i class="fas fa-exclamation-triangle mr-2"></i> Trigger Failed');
                }
                // Re-enable button shortly after triggering (console shows live status)
                 setTimeout(function() {
                    $btn.removeClass("btn-success btn-danger").addClass("btn-warning") // Reset color too
                        .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                        .prop('disabled', false);
                 }, 3000); 
            },
            error: function(xhr, status, error) {
                console.error(`AJAX error calling trigger endpoint ${triggerUrl}: Status: ${status}, Error: ${error}`);
                $logOutput.append(document.createTextNode(`[ERROR] Network or server error attempting to trigger restart: ${status}\n`));
                $logOutput.scrollTop($logOutput[0].scrollHeight); // Scroll down
                stopLogPolling('Error triggering restart.');
                 $btn.removeClass("btn-warning").addClass("btn-danger")
                    .html('<i class="fas fa-exclamation-triangle mr-2"></i> Trigger Error');
                // Re-enable button
                 setTimeout(function() {
                    $btn.removeClass("btn-danger").addClass("btn-warning")
                        .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                        .prop('disabled', false);
                 }, 3000);
            }
        });
    });

    // --- Event Listeners for Log Console Controls --- 
    $closeLogBtn.on('click', function() {
        $logWindow.fadeOut();
        stopLogPolling();
    });

    $refreshLogBtn.on('click', function() {
        // Restart polling from the beginning
        $logOutput.append(document.createTextNode('---- Log refreshed ----\n'));
        startLogPolling(false); // Restart polling, don't fade in again
    });

    $copyLogBtn.on('click', function() {
        const logText = $logOutput.text(); // Get text content
        navigator.clipboard.writeText(logText).then(function() {
            // Optional: Give feedback
            const $originalIcon = $copyLogBtn.html();
            $copyLogBtn.html('<i class="fas fa-check"></i>');
            setTimeout(() => { $copyLogBtn.html($originalIcon); }, 1500);
        }).catch(function(err) {
            console.error('Failed to copy log text: ', err);
            // Optional: Show error feedback
             const $originalIcon = $copyLogBtn.html();
            $copyLogBtn.html('<i class="fas fa-times"></i>');
            setTimeout(() => { $copyLogBtn.html($originalIcon); }, 1500);
        });
    });

    // --- Service Status Check ---
    const SERVICE_STATUS_URL = '/core/get-pystray-service-status/';
    const $serviceStatusIndicator = $('#serviceStatusIndicator');
    let serviceStatusCheckInterval = null;

    function checkServiceStatus() {
        $.ajax({
            url: SERVICE_STATUS_URL,
            type: 'GET',
            dataType: 'json',
            timeout: 5000,
            success: function(response) {
                if (response.status === 'running') {
                    $serviceStatusIndicator
                        .removeClass('badge-secondary badge-stopped')
                        .addClass('badge-running')
                        .html('<i class="fas fa-check-circle mr-1"></i> Running');
                } else {
                    $serviceStatusIndicator
                        .removeClass('badge-secondary badge-running')
                        .addClass('badge-stopped')
                        .html('<i class="fas fa-times-circle mr-1"></i> Stopped');
                }
            },
            error: function() {
                $serviceStatusIndicator
                    .removeClass('badge-secondary badge-running')
                    .addClass('badge-stopped')
                    .html('<i class="fas fa-times-circle mr-1"></i> Stopped');
            }
        });
    }

    // Start checking service status every 30 seconds
    checkServiceStatus(); // Initial check
    serviceStatusCheckInterval = setInterval(checkServiceStatus, 30000);

    // Function to refresh the loop status table
    function refreshLoopTable() {
        $.ajax({
            url: window.location.href,
            type: 'GET',
            dataType: 'html',
            timeout: 10000,
            success: function(html) {
                const newBody = $('<div>').html(html).find('tbody').first().html();
                $('tbody').first().html(newBody);
                sortTableAsc();
                applyRowColoring();
            }
        });
    }
    // Poll table refresh every 11 seconds
    setInterval(refreshLoopTable, 11000);

    // Clean up interval when page is unloaded
    $(window).on('unload', function() {
        if (serviceStatusCheckInterval) {
            clearInterval(serviceStatusCheckInterval);
        }
    });

});