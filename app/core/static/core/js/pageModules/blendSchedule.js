import { AddLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'
import { AddScheduleStopperButton, TableSorterButton, GHSSheetGenerator, CreateBlendLabelButton, EditLotNumButton } from '../objects/buttonObjects.js' 

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initializeBlendScheduleTooltips() {
    $('.blend-sheet-status').each(function() {
        const statusSpan = this;
        const jqStatusSpan = $(statusSpan);
        const existingTooltip = bootstrap.Tooltip.getInstance(statusSpan);
        if (existingTooltip) {
            existingTooltip.dispose();
        }

        const printHistoryJSON = jqStatusSpan.attr('data-print-history');
        const hasBeenPrinted = jqStatusSpan.attr('data-has-been-printed') === 'true';
        let tooltipTitle; // Will be set to the HTML string for the tooltip or undefined

        // Retrieve current user's username, expected to be set globally
        const rawCurrentUser = window.currentUserUsername || null;
        const currentUser = rawCurrentUser ? rawCurrentUser.trim() : null;

        if (printHistoryJSON && printHistoryJSON !== 'null' && printHistoryJSON.trim() !== '') {
            try {
                const printHistory = JSON.parse(printHistoryJSON);
                if (Array.isArray(printHistory) && printHistory.length > 0) {
                    let historyHtml = '<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>';
                    printHistory.forEach(entry => {
                        const printedAt = entry.printed_at ? new Date(entry.printed_at).toLocaleString() : (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A');
                        
                        let printerDisplay = 'Unknown User'; // Default assumption
                        const originalPrintedByUsername = entry.printed_by_username;
                        const userFromEntry = entry.user; // Get entry.user once

                        if (originalPrintedByUsername) { 
                            const trimmedOriginalUsername = originalPrintedByUsername.trim();
                            if (currentUser && trimmedOriginalUsername.toLowerCase() === currentUser.toLowerCase()) {
                                printerDisplay = "(You)"; 
                            } else {
                                printerDisplay = trimmedOriginalUsername; 
                            }
                        } else if (userFromEntry) { // Check if entry.user exists
                            const trimmedUserFromEntry = userFromEntry.trim();
                            if (currentUser && trimmedUserFromEntry.toLowerCase() === currentUser.toLowerCase()) {
                                printerDisplay = "(You)"; // Current user matches entry.user
                            } else if (trimmedUserFromEntry === "You") {
                                // This case handles optimistic updates that haven't been replaced by server data yet,
                                // or old data that literally stored "You". If currentUser is available, prefer that.
                                printerDisplay = "(You)"; 
                            } else {
                                printerDisplay = trimmedUserFromEntry; // Display the content of entry.user (e.g., another username)
                            }
                        } 
                        // If neither originalPrintedByUsername nor userFromEntry, it remains 'Unknown User'
                        
                        historyHtml += `<tr><td>${printerDisplay}</td><td>${printedAt}</td></tr>`;
                    });
                    historyHtml += '</tbody></table>';
                    tooltipTitle = historyHtml;

                    if (printHistory.length > 1) {
                        jqStatusSpan.addClass('has-multiple-prints');
                    } else {
                        jqStatusSpan.removeClass('has-multiple-prints');
                    }
                } else if (hasBeenPrinted) {
                    tooltipTitle = 'Printed (detailed history unavailable).';
                    jqStatusSpan.removeClass('has-multiple-prints');
                } else {
                    tooltipTitle = 'Blend sheet has not been printed.';
                    jqStatusSpan.removeClass('has-multiple-prints');
                }
            } catch (e) {
                console.error("Error parsing print history JSON:", e, printHistoryJSON);
                tooltipTitle = "Error loading print history.";
                jqStatusSpan.removeClass('has-multiple-prints');
            }
        } else if (hasBeenPrinted) {
            tooltipTitle = 'Printed (detailed history unavailable).';
            jqStatusSpan.removeClass('has-multiple-prints');
        } else { // Not printed and no history
            tooltipTitle = 'Blend sheet has not been printed.';
            jqStatusSpan.removeClass('has-multiple-prints');
        }

        if (tooltipTitle) {
            const newTooltip = new bootstrap.Tooltip(statusSpan, {
                title: tooltipTitle,
                html: true,
                sanitize: false,
                trigger: 'hover focus',
                placement: 'top',
                boundary: 'scrollParent', // or 'viewport' or specific element
                customClass: 'print-history-tooltip', // Ensure this class matches CSS
                container: 'body' // Match lotNumRecords.js
            });
            // Ensure Bootstrap's internal title is updated if already initialized then changed
            $(statusSpan).attr('data-bs-original-title', tooltipTitle);
        }
    });
}

$(document).ready(function(){
    new GHSSheetGenerator();
    new ShiftSelectCheckBoxes();
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blend-area');
    
    const noteRowButtonElement = document.getElementById("noteRowButton"); // Get the button element once

    if (blendArea == 'Hx') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-hx`);
    } else if (blendArea == 'Dm') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-dm`);
    } else if (blendArea == 'Totes') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-totes`);
    } else if (blendArea == 'Desk_1') {
        new TableSorterButton('deskScheduleTable', 'Short');
        if (noteRowButtonElement) { // Check if the button exists
            new AddScheduleStopperButton(noteRowButtonElement, 'Desk_1');
        }
    } else if (blendArea == 'Desk_2') {
        new TableSorterButton('deskScheduleTable', 'Short');
        if (noteRowButtonElement) { // Check if the button exists
            new AddScheduleStopperButton(noteRowButtonElement, 'Desk_2');
        }
    }

    const editLotButtons = document.querySelectorAll('.editLotButton');
    editLotButtons.forEach(button => {
        let thisEditLotNumButton = new EditLotNumButton(button);
    });
 
    initializeBlendScheduleTooltips(); // Initial call on page load
  
    const blendLabelLinks = document.querySelectorAll(".blendLabelLink");
    let dialog = document.querySelector('#blendLabelDialog');
    blendLabelLinks.forEach(function(link) {
        let thisCreateBlendLabelButton = new CreateBlendLabelButton(link);
        link.addEventListener('click', function(event) {
            dialog.showModal();
            $("#printButton").attr("data-encoded-item-code", event.currentTarget.getAttribute("data-encoded-item-code"));
            $("#printButton").attr("data-lot-number", event.currentTarget.getAttribute("data-lot-number"));
            const batchQuantity = event.currentTarget.getAttribute("data-lot-quantity");
            const labelQuantity = Math.ceil(batchQuantity / 250)*2;
            $("#labelQuantity").val(labelQuantity);
        });
    });

    $(document).on('click', '.generate-excel-macro-trigger', function(event) {
        event.preventDefault();
        const $this = $(this);
        const macroName = $this.data('macro-name');
        const itemCode = $this.data('item-code');
        const itemDescription = $this.data('item-description');
        const lotNumber = $this.data('lot-number');
        const lotQuantity = $this.data('lot-quantity');
        const line = $this.data('line'); 
        const runDate = $this.data('run-date'); 

        const $statusSpan = $this.closest('tr').find('.blend-sheet-status');
        const hasBeenPrinted = $statusSpan.attr('data-has-been-printed') === 'true';
        const recordId = $statusSpan.data('record-id');

        let proceedWithPrint = true; 

        // Conditional confirmation for reprints, mirroring lotNumRecords.js logic
        if (hasBeenPrinted) {
            if (macroName === 'generateProductionPackage') {
                if (!confirm(`This production package (or its blend sheet component) for lot ${lotNumber} has been printed before. Reprint?`)) {
                    proceedWithPrint = false;
                }
            } else if (macroName === 'blndSheetGen') { 
                if (!confirm(`Blend sheet for lot ${lotNumber} has been printed before. Reprint?`)) {
                    proceedWithPrint = false;
                }
            }
        }

        if (!proceedWithPrint) {
            return; 
        }

        $this.closest('tr').addClass('printing-row-style');
        const originalButtonText = $this.html();
        $this.html('Processing... <i class="fas fa-spinner fa-spin"></i>');
        $this.addClass('disabled-link');

        const payload = {
            macro_to_run: macroName,
            data_for_macro: [lotQuantity, lotNumber, line, itemDescription, runDate, itemCode],
            record_id: recordId 
        };

        $.ajax({
            url: '/core/trigger-excel-macro-execution/', // ALIGNED URL
            type: 'POST',
            data: JSON.stringify(payload), // ALIGNED: Send as JSON string
            contentType: 'application/json; charset=utf-8', // ALIGNED: Set content type to JSON
            dataType: 'json', // Expect JSON response
            headers: {
                'X-CSRFToken': getCookie('csrftoken') // ALIGNED: CSRF token in header for JSON post
            },
            timeout: 400000, 
            success: function(response) {
                $this.closest('tr').removeClass('printing-row-style');
                $this.html(originalButtonText);
                $this.removeClass('disabled-link');

                if (response.status === 'success' || (response.original_status_code && response.original_status_code === 200)) {
                    let successMsg = response.message || "Macro triggered successfully!";
                    if (macroName === 'generateProductionPackage') {
                        successMsg = "Blend sheets printed";
                    }
                    alert(successMsg);
                    if ($statusSpan.length) {
                        const now = new Date();
                        // Format date as "Jul 29, 2024" or similar
                        const formattedDate = `${now.toLocaleString('default', { month: 'short' })} ${now.getDate()}, ${now.getFullYear()}`;
                        $statusSpan.text(formattedDate);
                        $statusSpan.attr('data-has-been-printed', 'true');
                        
                        let newPrintLogEntry = {
                            user: "You", // Simplified as per lotNumRecords.js client-side update
                            timestamp: now.toISOString(), // Standard ISO string
                        };
                        try {
                            let history = JSON.parse($statusSpan.attr('data-print-history') || '[]');
                            history.unshift(newPrintLogEntry); 
                            $statusSpan.attr('data-print-history', JSON.stringify(history));
                            initializeBlendScheduleTooltips(); 
                        } catch (e) {
                            console.error("Error updating print history data client-side:", e);
                            initializeBlendScheduleTooltips(); 
                        }
                    }
                } else {
                    alert('Error: ' + (response.message || 'Unknown error occurred.'));
                }
            },
            error: function(xhr, status, error) {
                $this.closest('tr').removeClass('printing-row-style');
                $this.html(originalButtonText);
                $this.removeClass('disabled-link');
                let errorMsg = 'An error occurred while triggering the macro.';
                if (status === 'timeout') {
                    errorMsg = 'The request timed out. The process might still be running in the background. Please check Excel.';
                } else if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMsg = xhr.responseJSON.message;
                } else if (xhr.statusText) {
                    errorMsg = `Error: ${xhr.status} - ${xhr.statusText}`;
                } else if (xhr.responseText) {
                    try {
                        const errResponse = JSON.parse(xhr.responseText);
                        errorMsg = errResponse.message || errResponse.details || errorMsg;
                    } catch (e) { /* Ignore parsing error, use default */ }
                }
                alert(errorMsg);
                console.error("Error triggering macro: ", status, error, xhr.responseText);
            }
        });
    });
});