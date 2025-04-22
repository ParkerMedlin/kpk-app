$(document).ready(function() {
    let currentTime = new Date();
    const tableRows = document.querySelectorAll("tbody tr");
    tableRows.forEach(function(row) {
        // Get the timestamp cell value
        let timestampCell = row.querySelector("td:nth-child(2)").textContent;
        let timestamp = new Date(timestampCell);
        // Calculate the time difference in minutes
        let timeDifference = (currentTime - timestamp) / (1000 * 60);
        // Check if the time difference is greater than 6 minutes
        if (timeDifference > 6) {
            row.className = "Failure";
        }
    });

    // Restart loop functionality
    $("#restartLoopBtn").on("click", function() {
        // Disable the button to prevent multiple clicks
        const $btn = $(this);
        $btn.prop("disabled", true).html('<i class="fas fa-spinner fa-spin mr-2"></i> Restarting...');
        
        // Define potential host URLs to try (in order of preference)
        const hostUrls = [
            "http://host.docker.internal:9999/trigger-restart", // Docker for Windows/Mac recommended name
            "http://localhost:9999/trigger-restart",            // Direct localhost (may work in some configs)
            "http://127.0.0.1:9999/trigger-restart"             // Explicit loopback IP
        ];
        
        // Function to try next URL in sequence
        function tryNextUrl(index) {
            if (index >= hostUrls.length) {
                // All URLs failed
                console.error("All host resolution attempts failed");
                $btn.removeClass("btn-warning").addClass("btn-danger")
                    .html('<i class="fas fa-exclamation-triangle mr-2"></i> Restart Failed');
                
                setTimeout(function() {
                    $btn.removeClass("btn-danger").addClass("btn-warning")
                        .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                        .prop("disabled", false);
                }, 5000);
                return;
            }
            
            // Try current URL
            $.ajax({
                url: hostUrls[index],
                type: "GET",
                timeout: 2000, // Shorter timeout for faster fallback
                success: function(response) {
                    console.log("Restart request successful:", response);
                    $btn.removeClass("btn-warning").addClass("btn-success")
                        .html('<i class="fas fa-check mr-2"></i> Restart Initiated');
                    
                    setTimeout(function() {
                        $btn.removeClass("btn-success").addClass("btn-warning")
                            .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                            .prop("disabled", false);
                    }, 5000);
                },
                error: function(xhr, status, error) {
                    console.warn(`Host resolution attempt failed for ${hostUrls[index]}:`, error);
                    // Try next URL in sequence
                    tryNextUrl(index + 1);
                }
            });
        }
        
        // Start with first URL
        tryNextUrl(0);
    });
});