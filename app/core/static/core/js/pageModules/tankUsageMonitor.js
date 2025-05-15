// New JS module for Tank Usage Monitor
import { ItemReferenceFieldPair } from '../objects/lookupFormObjects.js';
import { getAllBOMFields } from '../requestFunctions/requestFunctions.js';

$(document).ready(function () {
    const tankId = $('#tankId').text().trim();
    let startGallons = null;
    let isTracking = false;
    let itemConfirmed = false;
    let confirmedItemCode = null;

    const $itemInput = $('#itemCodeInput');
    const $itemDescriptionInput = $('#itemDescriptionInput');
    const $confirmBtn = $('#confirmItemBtn');
    const $startBtn = $('#startBtn');
    const $stopBtn = $('#stopBtn');
    const $resetBtn = $('#resetBtn');
    const $nextBlendBtn = $('#nextBlendBtn');
    const $itemStatus = $('#itemConfirmStatus');
    const $currentGallons = $('#currentGallons');
    const $gallonsDispensed = $('#gallonsDispensed');
    const $radarStatus = $('#radarStatus');
    const $startRequirementMsg = $('#startRequirementMsg');

    let currentUsageLog = {}; // To store data for the current usage event

    // --- Setup Autocomplete --- 
    const blendBOMFields = getAllBOMFields('blend');
    const itemFieldPair = new ItemReferenceFieldPair($itemInput[0], $itemDescriptionInput[0]);
    itemFieldPair.BOMFields = blendBOMFields;
    itemFieldPair.setUpAutofill($itemInput[0], $itemDescriptionInput[0]);

    // -- Helper functions --
    function fetchCurrentGallons() {
        return $.getJSON(`/core/api/get-single-tank-level/${tankId}/`).then(resp => resp).catch(() => {
            return { status: 'error', error_message: 'Radar unreachable' };
        });
    }

    function updateGallonsDisplay(gallons) {
        $currentGallons.text(gallons.toFixed(2));
    }

    function setError(message) {
        $radarStatus.text(message).prop('hidden', false);
    }

    function clearError() {
        $radarStatus.prop('hidden', true);
    }

    // -- Periodic update loop --
    function periodicUpdate() {
        fetchCurrentGallons().then(data => {
            if (data.status === 'ok') {
                clearError();
                const gallons = parseFloat(data.gallons);
                updateGallonsDisplay(gallons);
                // --- VIZIER'S DIAGNOSTIC LOG ---
                console.log(`Periodic Update: isTracking=${isTracking}, startGallons=${startGallons}, currentGallons=${gallons}`);
                if (isTracking && startGallons !== null) {
                    const dispensed = startGallons - gallons;
                    // --- VIZIER'S DIAGNOSTIC LOG ---
                    console.log(`Calculating Dispensed: startGallons=${startGallons} - currentGallons=${gallons} = ${dispensed}`);
                    $gallonsDispensed.text(dispensed.toFixed(2));
                }
            } else {
                setError('Radar Unreachable, notify Anthony Hale');
            }
        });
    }

    const intervalId = setInterval(periodicUpdate, 1000); // 1 second update
    periodicUpdate(); // Initial fetch

    // -- Item confirmation logic --
    $confirmBtn.on('click', () => {
        const itemCode = $itemInput.val().trim();
        if (!itemCode) {
            $itemStatus.text('Enter an item code.').addClass('status-error');
            return;
        }
        $.post('/core/api/validate-blend-item/', { item_code: itemCode })
            .done(resp => {
                if (resp.valid) {
                    itemConfirmed = true;
                    confirmedItemCode = itemCode;
                    $itemStatus.removeClass('status-error').addClass('status-success').text(`Confirmed: ${resp.item_description}`);
                    $itemInput.prop('disabled', true);
                    $itemDescriptionInput.prop('disabled', true);
                    $confirmBtn.prop('disabled', true);
                    $startRequirementMsg.hide();
                    $startBtn.prop('disabled', false);
                    document.title = `Tank Usage Monitor - ${resp.item_description}`;
                } else {
                    $itemStatus.removeClass('status-success').addClass('status-error').text(resp.error);
                    itemConfirmed = false;
                }
            })
            .fail(() => {
                $itemStatus.removeClass('status-success').addClass('status-error').text('Validation failed.');
            });
    });

    // -- Tracking controls --
    function startTracking() {
        fetchCurrentGallons().then(data => {
            if (data.status === 'ok') {
                startGallons = parseFloat(data.gallons);
                isTracking = true;

                // --- VIZIER'S LOGGING INITIATION ---
                currentUsageLog = {
                    tank_identifier: tankId,
                    item_code: confirmedItemCode,
                    start_gallons: startGallons,
                    start_time: new Date().toISOString() 
                };
                // --- END VIZIER'S LOGGING ---

                $startBtn.prop('disabled', true);
                $stopBtn.prop('disabled', false);
                $nextBlendBtn.prop('disabled', true);
                $resetBtn.prop('disabled', true);
                $gallonsDispensed.text('0.00');
            } else {
                setError('Radar Unreachable, notify Anthony Hale');
            }
        });
    }

    function stopTracking() {
        isTracking = false;
        $stopBtn.prop('disabled', true);
        $nextBlendBtn.prop('disabled', false);
        $resetBtn.prop('disabled', false);

        // --- VIZIER'S LOGGING COMPLETION ---
        if (currentUsageLog.start_time) { // Ensure we have a start event
            const stopGallons = parseFloat($currentGallons.text());
            const dispensed = currentUsageLog.start_gallons - stopGallons;
            
            currentUsageLog.stop_gallons = stopGallons;
            currentUsageLog.gallons_dispensed = dispensed;
            currentUsageLog.stop_time = new Date().toISOString();

            $.ajax({
                url: '/core/api/log-tank-usage/', // Our new sacred endpoint
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(currentUsageLog),
                headers: { "X-CSRFToken": getCookie("csrftoken") }, // For Django's protection
                success: function(response) {
                    console.log("Tank usage logged successfully:", response);
                },
                error: function(xhr, status, error) {
                    console.error("Error logging tank usage:", error);
                    // Optionally, inform the user of the failure
                }
            });
            currentUsageLog = {}; // Reset for the next cycle
        }
        // --- END VIZIER'S LOGGING ---
    }

    function resetAll() {
        isTracking = false;
        startGallons = null;
        itemConfirmed = false;
        confirmedItemCode = null;
        $itemInput.val('').prop('disabled', false);
        $itemDescriptionInput.val('').prop('disabled', false);
        $confirmBtn.prop('disabled', false);
        $startBtn.prop('disabled', true);
        $stopBtn.prop('disabled', true);
        $nextBlendBtn.prop('disabled', true);
        $resetBtn.prop('disabled', true);
        $gallonsDispensed.text('0.00');
        $itemStatus.text('');
        $startRequirementMsg.show();
        document.title = 'Tank Usage Monitor';
    }

    function prepareNextBlend() {
        if (confirm("Prepare for next blend? This clears the current item and resets dispensed gallons.")) {
            itemConfirmed = false;
            confirmedItemCode = null;
            $itemInput.val('').prop('disabled', false);
            $itemDescriptionInput.val('').prop('disabled', false);
            $confirmBtn.prop('disabled', false);
            $startBtn.prop('disabled', true);
            $gallonsDispensed.text('0.00');
            $itemStatus.text('');
            $startRequirementMsg.show();
            document.title = 'Tank Usage Monitor';
        }
    }

    $startBtn.on('click', startTracking);
    $stopBtn.on('click', stopTracking);
    $resetBtn.on('click', resetAll);
    $nextBlendBtn.on('click', prepareNextBlend);

    // Helper function to get CSRF token (if not already available)
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

    $(window).on('beforeunload', () => {
        clearInterval(intervalId);
    });
}); 