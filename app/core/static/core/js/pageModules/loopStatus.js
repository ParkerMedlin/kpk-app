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
        
        // --- Call Django Backend Endpoint --- 
        const djangoUrl = "/core/trigger-restart/"; // URL defined in core/urls.py
        console.log(`Sending request to Django backend: ${djangoUrl}`);

        $.ajax({
            url: djangoUrl,
            type: "GET",
            dataType: "json", // Expect JSON response from Django
            timeout: 10000, // Slightly longer timeout to allow for backend processing
            success: function(response) {
                // Check the status field in the JSON response from Django
                if (response.status === 'success') {
                    console.log("Django backend reported success:", response.message);
                    $btn.removeClass("btn-warning").addClass("btn-success")
                        .html('<i class="fas fa-check mr-2"></i> Restart Initiated');
                } else {
                    // Handle errors reported by the Django backend
                    console.error("Django backend reported error:", response.message);
                    $btn.removeClass("btn-warning").addClass("btn-danger")
                        .html('<i class="fas fa-exclamation-triangle mr-2"></i> Trigger Failed');
                    // Optionally display response.message to the user in an alert or modal
                    // alert(`Failed to trigger restart: ${response.message}`);
                }
                
                // Re-enable button after delay, regardless of success/failure
                setTimeout(function() {
                    $btn.removeClass("btn-success btn-danger").addClass("btn-warning")
                        .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                        .prop("disabled", false);
                }, 5000);
            },
            error: function(xhr, status, error) {
                // Handle AJAX errors (e.g., network issue reaching Django, 500 server error)
                console.error(`AJAX error calling Django endpoint ${djangoUrl}: Status: ${status}, Error: ${error}, Response: ${xhr.responseText}`);
                $btn.removeClass("btn-warning").addClass("btn-danger")
                    .html('<i class="fas fa-exclamation-triangle mr-2"></i> Error');
                
                // Re-enable button after delay
                setTimeout(function() {
                    $btn.removeClass("btn-danger").addClass("btn-warning")
                        .html('<i class="fas fa-sync-alt mr-2"></i> Restart Data Looper')
                        .prop("disabled", false);
                }, 5000);
            }
        });
    });
});