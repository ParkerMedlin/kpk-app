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
});