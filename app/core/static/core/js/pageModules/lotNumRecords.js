import { DeleteLotNumModal, AddLotNumModal, EditLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { CreateCountListButton, GHSSheetGenerator, CreateBlendLabelButton, EditLotNumButton } from '../objects/buttonObjects.js'
import { BlendScheduleWebSocket } from '../objects/webSocketObjects.js';

// Notification helper
function showPrintNotification(type, title, message) {
    const notificationId = `print-notification-${Date.now()}`;
    const bgClass = type === 'success' ? 'bg-success' : type === 'info' ? 'bg-info' : 'bg-danger';
    const iconClass = type === 'success' ? 'fa-check-circle' : type === 'info' ? 'fa-info-circle' : 'fa-exclamation-circle';
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
    setTimeout(() => {
        const notification = document.getElementById(notificationId);
        if (notification) notification.remove();
    }, 4000);
}
window.showPrintNotification = showPrintNotification;

// --- Functions to add data-blend-id to table rows for WebSocket updates ---
function addDataAttributesToLotNumRecordRows() {
    const tables = document.querySelectorAll('table.table'); // Target the specific table if possible
    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            if (!row.hasAttribute('data-blend-id')) { // Process only if data-blend-id is not already set
                const scheduleEntryId = row.getAttribute('data-schedule-entry-id');

                if (scheduleEntryId && scheduleEntryId.trim() !== '' && scheduleEntryId !== 'null' && scheduleEntryId !== 'undefined') {
                    row.setAttribute('data-blend-id', scheduleEntryId);
                    // console.log(`Set data-blend-id=${scheduleEntryId} (from schedule-entry-id) for row.`);
                } else {
                    // Fallback to LotNumRecord.id if no schedule-entry-id is found
                    const statusSpan = row.querySelector('.blend-sheet-status[data-record-id]');
                    if (statusSpan) {
                        const lotNumRecordId = statusSpan.getAttribute('data-record-id');
                        if (lotNumRecordId && lotNumRecordId !== 'null' && lotNumRecordId !== '' && lotNumRecordId !== 'undefined') {
                            row.setAttribute('data-blend-id', lotNumRecordId);
                            // console.log(`Set data-blend-id=${lotNumRecordId} (from lotNumRecordId) for row as fallback.`);
                        }
                    }
                }
            }
        });
    });
}

function enhanceLotNumRecordTableForWebSockets() {
    addDataAttributesToLotNumRecordRows(); // Initial pass

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'TR') {
                        // If a new row is added, ensure it gets the attribute.
                        // This might be a single row, so query within it.
                        if (!node.hasAttribute('data-blend-id')){
                            const statusSpan = node.querySelector('.blend-sheet-status[data-record-id]');
                            if (statusSpan) {
                                const recordId = statusSpan.getAttribute('data-record-id');
                                if (recordId && recordId !== 'null' && recordId !== '' && recordId !== 'undefined') {
                                    node.setAttribute('data-blend-id', recordId);
                                }
                            }
                        }
                    }
                });
            }
        });
    });

    const tableBodies = document.querySelectorAll('table.table tbody');
    tableBodies.forEach(tbody => {
        observer.observe(tbody, { childList: true });
    });
}
// --- End functions for data-blend-id ---

$(document).ready(function(){
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const thisGHSSheetGenerator = new GHSSheetGenerator();
    let thisScheduleItemModal;

    const $addLotNumButton = $("#addLotNumButton");
    const $batchDeleteButton = $('#batchDeleteButton');
    const $createCountListButton = $("#create_list");
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editLotButtons = document.querySelectorAll('.editLotButton');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");
    const $addToScheduleLinks = $(".addToScheduleLink");

    const thisAddLotNumModal = new AddLotNumModal();
    $duplicateBtns.each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    $addLotNumButton.click(function(e) {
        e.preventDefault();
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    thisAddLotNumModal.formElement.prop("action", "/core/add-lot-num-record/?redirect-page=lot-num-records")

    
    const thisDeleteLotNumModal = new DeleteLotNumModal();

    const thisEditLotNumModal = new EditLotNumModal();
    editLotButtons.forEach(button => {
        let thisEditLotNumButton = new EditLotNumButton(button);
    })

    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            let item_codes = [];
            $('td input:checked').each(function() {
                item_codes.push($(this).attr("name"));
            });
            $createCountListButton.show();
            $batchDeleteButton.show();
            $batchDeleteButton.attr("dataitemid", item_codes);
        });
    });
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteLotNumModal.setModalButtons);
    });
    $batchDeleteButton.click(thisDeleteLotNumModal.setModalButtons);

    const thisCreateCountListButton = new CreateCountListButton();

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

    // const thisZebraPrintButton = new ZebraPrintButton(document.querySelector('#printButton'));

    const excelMacroTriggerLinks = document.querySelectorAll(".generate-excel-macro-trigger");
    excelMacroTriggerLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default anchor behavior
            const targetElement = event.currentTarget;
            const macroName = targetElement.getAttribute("data-macro-name");
            const itemCode = targetElement.getAttribute("data-item-code");
            const itemDescription = targetElement.getAttribute("data-item-description");
            const lotNumber = targetElement.getAttribute("data-lot-number");
            const parentRow = targetElement.closest('tr'); // Get the closest parent row

            let proceedWithPrint = true;
            // Confirmation for re-print should apply to the combined package if it includes a blend sheet.
            if ((macroName === "blndSheetGen" || macroName === "generateProductionPackage") && parentRow) {
                const statusSpan = parentRow.querySelector('.blend-sheet-status');
                if (statusSpan && statusSpan.getAttribute('data-has-been-printed') === 'true') {
                    if (!confirm("This production package (or its blend sheet component) has been printed before. Do you want to reprint it? This may result in duplicate documents.")) {
                        proceedWithPrint = false;
                    }
                }
            }
            if (!proceedWithPrint) {
                return; // Abort if user cancels reprint
            }

            let macroData = [];
            let statusMessage = "";

            // Updated logic for macroName
            if (macroName === "generateProductionPackage") {
                const lotQuantity = targetElement.getAttribute("data-lot-quantity");
                const line = targetElement.getAttribute("data-line");
                const runDate = targetElement.getAttribute("data-run-date"); // Expected in YYYY-MM-DD
                macroData = [lotQuantity, lotNumber, line, itemDescription, runDate, itemCode];
                statusMessage = '<i class="fas fa-spinner fa-spin"></i> Printing Blend Sheets...';
            } else if (macroName === "blndSheetGen") { // Kept for potential direct call, though UI might remove it
                const lotQuantity = targetElement.getAttribute("data-lot-quantity");
                const line = targetElement.getAttribute("data-line");
                const runDate = targetElement.getAttribute("data-run-date");
                macroData = [lotQuantity, lotNumber, line, itemDescription, runDate, itemCode];
                statusMessage = '<i class="fas fa-spinner fa-spin"></i> Generating Blend Sheet...';
            } else {
                alert("Unknown macro type selected!");
                return;
            }

            const payload = {
                macro_to_run: macroName,
                data_for_macro: macroData
                // components_for_pick_sheet will be added by the Django view for generateProductionPackage
            };

            const originalText = targetElement.innerHTML;
            targetElement.innerHTML = statusMessage; 
            targetElement.style.pointerEvents = 'none'; 
            if (parentRow) {
                parentRow.classList.add('printing-row-style');
                // Consider disabling other buttons/links in the row if necessary
                // parentRow.querySelectorAll('a, button').forEach(el => el.style.pointerEvents = 'none');
            }

            fetch('/core/trigger-excel-macro-execution/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Django's CSRF token needs to be included if not using @csrf_exempt on the view
                    // and if you're not using a global AJAX setup for CSRF.
                    // For simplicity, assuming @csrf_exempt or global CSRF setup.
                    'X-CSRFToken': getCookie('csrftoken') // Ensure you have a getCookie function
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    // Try to parse error from server if JSON, otherwise use status text
                    return response.json().then(errData => {
                        throw new Error(errData.message || errData.details || `Server error: ${response.status} ${response.statusText}`);
                    }).catch(() => {
                         throw new Error(`Request failed: ${response.status} ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Reset UI elements before showing notification
                targetElement.innerHTML = originalText; 
                targetElement.style.pointerEvents = 'auto'; 
                if (parentRow) {
                    parentRow.classList.remove('printing-row-style');
                }

                console.log("Macro trigger response:", data);
                if (data.status === 'queued') {
                    let queueMsg = data.message || "Print job queued successfully!";
                    if (macroName === 'generateProductionPackage') {
                        queueMsg = "Production package print job queued. Processing...";
                    } else if (macroName === 'blndSheetGen') {
                        queueMsg = "Blend sheet print job queued. Processing...";
                    }
                    window.showPrintNotification('info', 'Print Queued', queueMsg);
                    
                    // Optimistically update the print status UI
                    const statusSpan = parentRow ? parentRow.querySelector('.blend-sheet-status') : null;
                    if (statusSpan) {
                        const currentUser = window.currentUserUsername || 'You'; // Assuming global var availability
                        const timestamp = new Date().toISOString();
                        
                        statusSpan.setAttribute('data-has-been-printed', 'true');
                        statusSpan.classList.add('printed'); // For styling consistency
                        
                        let printHistory = [];
                        try {
                            const existingHistory = statusSpan.getAttribute('data-print-history');
                            if (existingHistory && existingHistory !== 'null') {
                                printHistory = JSON.parse(existingHistory);
                            }
                        } catch (e) {
                            console.error("Error parsing existing print history for optimistic update:", e);
                        }
                        
                        printHistory.push({
                            user: currentUser,
                            printed_by_username: currentUser, // Align with blendSchedule.js structure
                            timestamp: timestamp,
                            printed_at: timestamp, // Align with blendSchedule.js structure
                            job_id: data.job_id 
                        });
                        
                        statusSpan.setAttribute('data-print-history', JSON.stringify(printHistory));
                        initializePrintStatusTooltips(); // Reinitialize tooltips to show new history
                    }
                } else if (data.status === 'success') {
                    let successMessage = "Action completed successfully!";
                    if (macroName === 'generateProductionPackage') {
                        successMessage = "Blend Sheets and associated documents printed successfully!";
                    } else if (macroName === 'blndSheetGen') {
                        successMessage = "Blend Sheet printed successfully!";
                    }
                    window.showPrintNotification('success', 'Print Complete', successMessage);
                    console.log("✅ Print successful - status will be updated via WebSocket");
                } else if (data.status === 'pending_implementation') {
                    window.showPrintNotification('warn', 'Action Pending', data.message || 'This feature is not yet fully implemented in the systray service.');
                } else if (data.status === 'deprecated') {
                    window.showPrintNotification('warn', 'Action Deprecated', data.message || 'This feature is no longer supported directly. Use the new combined functionality.');
                } else { // Other errors reported by the server with a valid JSON response
                    window.showPrintNotification('error', 'Print Error', data.message || 'Unknown error from service.');
                }
            })
            .catch(error => {
                // Reset UI elements on error as well
                targetElement.innerHTML = originalText; 
                targetElement.style.pointerEvents = 'auto'; 
                if (parentRow) {
                    parentRow.classList.remove('printing-row-style');
                }
                console.error('Error triggering Excel macro:', error);
                window.showPrintNotification('error', 'Request Failed', `Failed to trigger Excel macro. ${error.message}`);
            })
            .finally(() => {
                // Original .finally() logic for UI reset is now handled in .then() and .catch()
                // to ensure it executes before notifications.
                // This block can be empty or used for other cleanup if necessary.
            });
        });
    });

    // Helper function to get CSRF token (if not already globally available)
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

    // --- New: Initialize Tooltips for Print Status ---
    function initializePrintStatusTooltips() {
        // console.log("Initializing print status tooltips...");
        const statusSpans = document.querySelectorAll('.blend-sheet-status');

        statusSpans.forEach(span => {
            const existingTooltip = bootstrap.Tooltip.getInstance(span);
            if (existingTooltip) {
                existingTooltip.dispose();
            }

            const recordId = span.dataset.recordId || 'N/A'; // Get record ID for better logging
            const historyData = span.getAttribute('data-print-history');
            // console.log(`Processing span for record ID: ${recordId}. Has data-print-history attribute: ${span.hasAttribute('data-print-history')}`);
            // console.log(`Span history data attribute for ${recordId}:`, historyData);


            let titleContentForTooltip;

            if (historyData && historyData !== 'null' && historyData.trim() !== '') {
                // This span is expected to have history (it has the data-print-history attribute)
                // It might also have the initial title="Loading print history..."
                try {
                    const history = JSON.parse(historyData);
                    if (Array.isArray(history) && history.length > 0) {
                        // De-duplicate history before rendering
                        const uniqueHistory = [];
                        const seenEntries = new Set();
                        // Sort by timestamp descending to keep the latest if there are true duplicates only differing by ms
                        const sortedHistory = history.sort((a, b) => new Date(b.timestamp || b.printed_at || 0) - new Date(a.timestamp || a.printed_at || 0));

                        sortedHistory.forEach(entry => {
                            let entryKey;
                            // Try to use original_log_id if available from server, or job_id from optimistic update
                            if (entry.original_log_id) {
                                entryKey = `log-${entry.original_log_id}`;
                            } else if (entry.job_id) {
                                entryKey = `job-${entry.job_id}`;
                            } else if (entry.timestamp && (entry.user || entry.printed_by_username)) {
                                const user = entry.user || entry.printed_by_username;
                                const date = new Date(entry.timestamp);
                                // Key by user and timestamp rounded to the second
                                const roundedTimestamp = new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours(), date.getMinutes(), date.getSeconds()).toISOString();
                                entryKey = `${user}-${roundedTimestamp}`;
                            } else {
                                // Fallback if critical fields are missing - less reliable
                                entryKey = JSON.stringify(entry); 
                            }

                            if (!seenEntries.has(entryKey)) {
                                uniqueHistory.push(entry);
                                seenEntries.add(entryKey);
                            }
                        });

                        let tableRows = '';
                        // Iterate over unique, sorted history (which is now uniqueHistory, but original sort order might be preferred for display)
                        // For display, let's re-sort uniqueHistory by timestamp ascending or use as is if optimistic is pushed to end.
                        // The uniqueHistory will naturally keep the first encountered if keys are identical.
                        // To ensure the most recent of near-duplicates is kept if original_log_id/job_id are missing, sorting by timestamp DESC before de-duping was done.
                        // For display, sort uniqueHistory ascending by timestamp.
                        uniqueHistory.sort((a,b) => new Date(a.timestamp || a.printed_at || 0) - new Date(b.timestamp || b.printed_at || 0));

                        uniqueHistory.forEach(entry => {
                            const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : (entry.printed_at ? new Date(entry.printed_at).toLocaleString() : 'N/A');
                            const user = entry.user || entry.printed_by_username || 'N/A'; // Handle both field names
                            // Adapt for current user display if necessary (e.g., show "(You)")
                            let displayUser = user;
                            const rawCurrentUser = window.currentUserUsername || null;
                            const currentUser = rawCurrentUser ? rawCurrentUser.trim().toLowerCase() : null;
                            if (currentUser && user.toLowerCase() === currentUser) {
                                displayUser = '(You)';
                            }

                            tableRows += `<tr><td>${displayUser}</td><td>${timestamp}</td></tr>`;
                        });
                        titleContentForTooltip = `<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>${tableRows}</tbody></table>`;
                        
                        // Apply/remove class for multiple prints indicator based on unique history
                        if (uniqueHistory.length > 1) {
                            span.classList.add('has-multiple-prints');
                        } else {
                            span.classList.remove('has-multiple-prints');
                        }
                    } else {
                        // No history entries or historyData was valid JSON but an empty array
                        titleContentForTooltip = 'No print history entries found.';
                        span.classList.remove('has-multiple-prints'); // Ensure no underline if no history
                    }
                } catch (e) {
                    console.error(`Error parsing print history JSON for record ID ${recordId}:`, e, "Raw data:", historyData);
                    titleContentForTooltip = 'Error loading print history.';
                }
            } else {
                // This span does NOT have a 'data-print-history' attribute or it's empty.
                // This typically means it's a "Not Printed" item from the template's else branch.
                // These spans do not have title="Loading print history..." and should not get a tooltip from this function.
                // console.log(`No data-print-history attribute found or it's empty for record ID ${recordId}. Skipping tooltip initialization for this span.`);
                span.classList.remove('has-multiple-prints'); // Ensure no underline if definitely not printed
                return; // IMPORTANT: Do not attempt to initialize a tooltip for these.
            }

            // If we have generated content (either the table, "No entries", or "Error loading"), then initialize the tooltip.
            // This ensures that items that started with title="Loading print history..." get updated.
            if (titleContentForTooltip) {
                // console.log(`Initializing tooltip for span record ID ${recordId} with new content.`);
                const newTooltip = new bootstrap.Tooltip(span, {
                    title: titleContentForTooltip,
                    html: true,
                    sanitize: false, 
                    customClass: 'print-history-tooltip',
                    trigger: 'hover focus',
                    container: 'body' // Append tooltip to body to avoid positioning/z-index issues
                });
                // Force update the attribute that Bootstrap uses to store the title, to ensure it reflects the new content.
                span.setAttribute('data-bs-original-title', titleContentForTooltip);
            } else {
                // This block should ideally not be reached if the logic above is sound.
                // It implies that a span had `data-print-history` but somehow `titleContentForTooltip` was not set.
                // console.warn(`Tooltip initialization skipped for record ID ${recordId} due to no titleContentForTooltip, though historyData might have been present. This is unexpected.`);
            }
        });
    }

    initializePrintStatusTooltips(); // Call on page load
    // --- End New Tooltip Initialization ---

    // Make the page-specific tooltip initializer globally available under the name
    // that BlendScheduleWebSocket might expect.
    window.initializeBlendScheduleTooltips = initializePrintStatusTooltips;

    // Initialize WebSocket for real-time updates
    if (typeof BlendScheduleWebSocket !== 'undefined') {
        // Check if it hasn't been initialized already by another script (highly unlikely for this setup)
        if (!window.blendScheduleWebSocket) {
            window.blendScheduleWebSocket = new BlendScheduleWebSocket();
            console.log("BlendScheduleWebSocket initialized on lotNumRecords.js for real-time status updates.");
        }
    } else {
        console.warn("⚠️ BlendScheduleWebSocket class not found - real-time updates disabled on lotNumRecords.js");
    }

    // Enhance table for WebSocket updates by adding data-blend-id to rows
    enhanceLotNumRecordTableForWebSockets();
});