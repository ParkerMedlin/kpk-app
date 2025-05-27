import { AddLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'
import { AddScheduleStopperButton, TableSorterButton, GHSSheetGenerator, CreateBlendLabelButton, EditLotNumButton } from '../objects/buttonObjects.js' 
import { BlendScheduleWebSocket } from '../objects/webSocketObjects.js';
import { TankSelectionModal } from '../objects/tankSelectionModal.js';

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
        button.addEventListener('click', function() {
            const lotId = this.getAttribute('data-lot-id');
            const editLotNumModal = new EditLotNumButton(lotId);
        });
    });

    // 🚰 TANK-AWARE BLEND MOVEMENT HANDLER
    $(document).on('click', 'a[href*="schedule-management-request/switch-schedules"]', function(e) {
        e.preventDefault(); // Prevent default navigation
        
        const $link = $(this);
        const $row = $link.closest('tr');
        
        // Extract move parameters from the link
        const originalHref = $link.attr('href');
        const urlParts = originalHref.split('/');
        const blendArea = urlParts[urlParts.length - 2]; // Second to last part
        const blendId = urlParts[urlParts.length - 1].split('?')[0]; // Last part before query params
        
        // Extract destination from URL parameters
        const url = new URL(originalHref, window.location.origin);
        const destinationDesk = url.searchParams.get('switch-to');
        
        // Extract hourshort value from the row
        const $shortCell = $row.find('td:nth-child(8)');
        const hourshortValue = $shortCell.attr('data-hour-short') || '999.0';
        
        // Show loading state on the link
        const originalText = $link.html();
        $link.html('<i class="fas fa-spinner fa-spin me-1"></i>Checking...');
        $link.addClass('disabled');
        
        // Check tank compatibility first
        const checkParams = new URLSearchParams({
            blend_area: blendArea,
            blend_id: blendId,
            destination_desk: destinationDesk,
            hourshort: hourshortValue
        });
        
        fetch(`/core/move-blend-with-tank-selection/?${checkParams}`)
            .then(response => response.json())
            .then(data => {
                // Restore link state
                $link.html(originalText);
                $link.removeClass('disabled');
                
                if (data.requires_tank_selection) {
                    // Show tank selection modal
                    if (window.tankSelectionModal) {
                        window.tankSelectionModal.show(data);
                    } else {
                        console.error("❌ Tank selection modal not available");
                        alert("Tank selection modal not available. Please refresh the page and try again.");
                    }
                } else if (data.success) {
                    // Show success notification
                    showMoveNotification('success', 'Move Successful', data.message);
                    // Refresh page to show changes
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    console.error("❌ Blend move failed:", data);
                    showMoveNotification('error', 'Move Failed', data.error || 'Unknown error occurred');
                }
            })
            .catch(error => {
                console.error("❌ Error during tank compatibility check:", error);
                // Restore link state
                $link.html(originalText);
                $link.removeClass('disabled');
                showMoveNotification('error', 'Move Failed', 'Network error occurred');
            });
    });
    
    // Helper function to show move notifications
    function showMoveNotification(type, title, message) {
        const notificationId = `move-notification-${Date.now()}`;
        const bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
        
        const notificationHTML = `
            <div id="${notificationId}" class="position-fixed top-0 end-0 p-3" style="z-index: 9999;">
                <div class="toast show ${bgClass} text-white" role="alert">
                    <div class="toast-header ${bgClass} text-white border-0">
                        <i class="fas ${iconClass} me-2"></i>
                        <strong class="me-auto">${title}</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', notificationHTML);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            const notification = document.getElementById(notificationId);
            if (notification) {
                notification.remove();
            }
        }, 4000);
    }

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
                    const alertBox = alert(successMsg);
                    setTimeout(() => {
                        if (alertBox) {
                            alertBox.close();
                        }
                    }, 3000);
                    // Note: Print status will be updated via WebSocket from the server
                    // This prevents duplicate entries in the tooltip history table
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

    // Initialize WebSocket for real-time updates
    if (typeof BlendScheduleWebSocket !== 'undefined') {
        window.blendScheduleWebSocket = new BlendScheduleWebSocket();
    } else {
        console.warn("⚠️ BlendScheduleWebSocket class not found - real-time updates disabled");
    }
});

document.addEventListener('DOMContentLoaded', function() {
    let blendScheduleWS = null;
    
    function initializeWebSocket() {
        if (!blendScheduleWS) {
            blendScheduleWS = new BlendScheduleWebSocket();
            window.blendScheduleWebSocket = blendScheduleWS;
        }
    }
    
    function addDataAttributesToRows() {
        const tables = document.querySelectorAll('table');
        const currentPageArea = getCurrentPageArea();
        
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                if (!row.hasAttribute('data-blend-id')) {
                    let blendIdSet = false;
                    
                    // STRATEGY 1: For Desk schedules - prioritize lot dropdown with database IDs
                    if (currentPageArea === 'Desk_1' || currentPageArea === 'Desk_2' || currentPageArea === 'LET_Desk') {
                        // Pattern: lotModDropdown{{ item.id | default:forloop.counter }}
                        const lotDropdownButton = row.querySelector('button[id^="lotModDropdown"]');
                        if (lotDropdownButton) {
                            const buttonId = lotDropdownButton.id;
                            const blendIdMatch = buttonId.match(/lotModDropdown(\d+)/);
                            if (blendIdMatch) {
                                const blendId = blendIdMatch[1];
                                // For desk schedules, prefer longer IDs (database IDs vs forloop.counter)
                                if (blendId.length >= 3) { // Database IDs are typically longer
                                    row.setAttribute('data-blend-id', blendId);
                                    blendIdSet = true;
                                }
                            }
                        }
                        
                        // Fallback: manage dropdown - Pattern: dropdownMenuButton1{{ item.id | default:forloop.counter }}
                        if (!blendIdSet) {
                            const manageDropdownButton = row.querySelector('button[id^="dropdownMenuButton1"]');
                            if (manageDropdownButton) {
                                const buttonId = manageDropdownButton.id;
                                const blendIdMatch = buttonId.match(/dropdownMenuButton1(\d+)/);
                                if (blendIdMatch) {
                                    const blendId = blendIdMatch[1];
                                    row.setAttribute('data-blend-id', blendId);
                                    blendIdSet = true;
                                }
                            }
                        }
                    }
                    
                    // STRATEGY 2: For Drum/Horix/Totes - prioritize blend-sheet-status data-record-id
                    if (!blendIdSet && (currentPageArea === 'Dm' || currentPageArea === 'Hx' || currentPageArea === 'Totes')) {
                        // Pattern: data-record-id="{{ item.lot_num_record_obj.id }}"
                        const statusSpan = row.querySelector('.blend-sheet-status[data-record-id]');
                        if (statusSpan) {
                            const recordId = statusSpan.getAttribute('data-record-id');
                            if (recordId && recordId !== 'null' && recordId !== '' && recordId !== 'undefined') {
                                row.setAttribute('data-blend-id', recordId);
                                blendIdSet = true;
                            }
                        }
                    }
                    
                    // STRATEGY 3: Universal fallback - any element with data-record-id
                    if (!blendIdSet) {
                        const elementWithRecordId = row.querySelector('[data-record-id]');
                        if (elementWithRecordId) {
                            const recordId = elementWithRecordId.getAttribute('data-record-id');
                            if (recordId && recordId !== 'null' && recordId !== '' && recordId !== 'undefined') {
                                row.setAttribute('data-blend-id', recordId);
                                blendIdSet = true;
                            }
                        }
                    }
                    
                    // STRATEGY 4: Final fallback - lot number method (for rows without database records)
                    if (!blendIdSet) {
                        const lotNumberCell = row.querySelector('.lot-number-cell[lot-number]');
                        if (lotNumberCell) {
                            const lotNumber = lotNumberCell.getAttribute('lot-number');
                            if (lotNumber && lotNumber !== 'N/A' && lotNumber !== '******' && lotNumber !== 'Not found.' && lotNumber.trim() !== '') {
                                const fallbackId = `lot_${lotNumber.replace(/[^a-zA-Z0-9]/g, '_')}`;
                                row.setAttribute('data-blend-id', fallbackId);
                                blendIdSet = true;
                            }
                        }
                    }
                    
                    // If no ID was set, this row will not receive WebSocket updates
                }
            });
        });
    }
    
    function getCurrentPageArea() {
        const url = window.location.href;
        if (url.includes('blend-area=Desk_1')) return 'Desk_1';
        if (url.includes('blend-area=Desk_2')) return 'Desk_2';
        if (url.includes('blend-area=LET_Desk')) return 'LET_Desk';
        if (url.includes('blend-area=Hx')) return 'Hx';
        if (url.includes('blend-area=Dm')) return 'Dm';
        if (url.includes('blend-area=Totes')) return 'Totes';
        if (url.includes('blend-area=Pails')) return 'Pails';
        if (url.includes('blend-area=all')) return 'all';
        return 'all';
    }
    
    function enhanceTableForWebSockets() {
        addDataAttributesToRows();
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'TR') {
                            addDataAttributesToRows();
                        }
                    });
                }
            });
        });
        
        const tables = document.querySelectorAll('table tbody');
        tables.forEach(tbody => {
            observer.observe(tbody, { childList: true });
        });
    }
    
    enhanceTableForWebSockets();
    initializeWebSocket();
});