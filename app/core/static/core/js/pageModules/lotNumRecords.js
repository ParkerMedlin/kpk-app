import { DeleteLotNumModal, AddLotNumModal, EditLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { CreateCountListButton, GHSSheetGenerator, CreateBlendLabelButton, EditLotNumButton } from '../objects/buttonObjects.js'

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
                console.log("Macro trigger response:", data);
                if (data.status === 'success') {
                    let successMessage = "Action completed successfully!";
                    if (macroName === 'generateProductionPackage') {
                        successMessage = "Blend Sheets and associated documents printed successfully!";
                    } else if (macroName === 'blndSheetGen') {
                        successMessage = "Blend Sheet printed successfully!";
                    } // Other specific messages could be added here if needed
                    alert(successMessage);

                    // Update UI on successful print if it was a package or blend sheet
                    if ((macroName === "blndSheetGen" || macroName === "generateProductionPackage") && parentRow) {
                        const statusSpan = parentRow.querySelector('.blend-sheet-status');
                        if (statusSpan) {
                            const now = new Date();
                            const formattedDate = `${now.toLocaleString('default', { month: 'short' })} ${now.getDate()}, ${now.getFullYear()}`;
                            // Update the text to show it's printed, but do NOT prematurely add the 'edited' indicator.
                            // The server-side template rendering is the source of truth for the 'edited' indicator on full page load.
                            statusSpan.innerHTML = formattedDate; 
                            statusSpan.setAttribute('data-has-been-printed', 'true');
                            
                            // Update tooltip data
                            let newPrintLogEntry = {
                                user: "You", // Or get actual username if available client-side (e.g. from a hidden field or JS var)
                                timestamp: now.toISOString(), // Store as ISO string for consistency
                                lot_number_at_print: lotNumber // Capture current lot number
                            };
                            try {
                                let history = JSON.parse(statusSpan.getAttribute('data-print-history') || '[]');
                                history.unshift(newPrintLogEntry); // Add to the beginning
                                statusSpan.setAttribute('data-print-history', JSON.stringify(history));

                                // After updating history, check if multiple prints and apply/remove class
                                if (history.length > 1) {
                                    statusSpan.classList.add('has-multiple-prints');
                                } else {
                                    statusSpan.classList.remove('has-multiple-prints');
                                }

                                // Re-initialize or update tooltip content if it was already active
                                initializePrintStatusTooltips(); // Re-init all tooltips for simplicity here
                            } catch (e) {
                                console.error("Error updating print history data:", e);
                            }
                        }
                    }
                    // --- End New UI Update ---
                } else if (data.status === 'pending_implementation') {
                    alert(`Action Pending: ${data.message || 'This feature is not yet fully implemented in the systray service.'}`);
                } else if (data.status === 'deprecated') {
                    alert(`Action Deprecated: ${data.message || 'This feature is no longer supported directly. Use the new combined functionality.'}`);
                } else {
                    alert(`Error triggering macro: ${data.message || 'Unknown error from service.'}`);
                }
            })
            .catch(error => {
                console.error('Error triggering Excel macro:', error);
                alert(`Failed to trigger Excel macro. ${error.message}`);
            })
            .finally(() => {
                targetElement.innerHTML = originalText; 
                targetElement.style.pointerEvents = 'auto'; 
                if (parentRow) {
                    parentRow.classList.remove('printing-row-style');
                    // Re-enable other buttons/links if they were disabled
                    // parentRow.querySelectorAll('a, button').forEach(el => el.style.pointerEvents = 'auto');
                }
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
                        let tableRows = '';
                        history.forEach(entry => {
                            const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A';
                            const user = entry.user !== undefined ? entry.user : 'N/A';
                            tableRows += `<tr><td>${user}</td><td>${timestamp}</td></tr>`;
                        });
                        titleContentForTooltip = `<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>${tableRows}</tbody></table>`;
                        
                        // Apply/remove class for multiple prints indicator
                        if (history.length > 1) {
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

});