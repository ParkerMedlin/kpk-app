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

    // --- Setup Autocomplete --- 
    // Fetch BOM fields filtered for blends ONLY
    const blendBOMFields = getAllBOMFields('blend');
    // Instantiate the lookup pair
    const itemFieldPair = new ItemReferenceFieldPair($itemInput[0], $itemDescriptionInput[0]);
    // Override the data source used by this specific instance
    itemFieldPair.BOMFields = blendBOMFields;
    // Manually trigger the setup with the correct (overridden) data
    // Note: This depends on the internal structure of ItemReferenceFieldPair.setUpAutofill
    // If setUpAutofill re-fetches data internally, this won't work and ItemReferenceFieldPair needs modification.
    // Assuming setUpAutofill uses the instance's BOMFields property:
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
                if (isTracking && startGallons !== null) {
                    const dispensed = startGallons - gallons;
                    $gallonsDispensed.text(dispensed.toFixed(2));
                }
            } else {
                setError('Radar Unreachable, notify Anthony Hale');
                // Auto-stop tracking on error
                if (isTracking) {
                    stopTracking();
                }
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
                    // Update page title with confirmed item
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

    // Clean up on page unload
    $(window).on('beforeunload', () => {
        clearInterval(intervalId);
    });
}); 