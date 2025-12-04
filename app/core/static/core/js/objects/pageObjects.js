import { getMaxProducibleQuantity, getURLParameter, getNewBlendInstructionInfo, getItemInfo } from '../requestFunctions/requestFunctions.js'
// import { getContainersFromCount } from '../requestFunctions/requestFunctions.js'
import { updateBlendInstructionsOrder, logContainerLabelPrint, updateCountCollection } from '../requestFunctions/updateFunctions.js'
// import { ItemReferenceFieldPair } from './lookupFormObjects.js'

// Initialize a cache for conversion data
const conversionCache = {};

function _convertQuantityIfNeeded(countRecordId, totalQuantity, recordType){
    // Get the item code from the parent tr element
    const countRecordElement = $(`[data-countrecord-id="${countRecordId}"]`).first();
    let itemCode = '';
    
    if (countRecordElement.length > 0) {
        // Find the parent tr with class countRow
        const parentRow = countRecordElement.closest('tr.countRow');
        if (parentRow.length > 0) {
            // Get the data-itemcode attribute from the parent row
            itemCode = parentRow.data('itemcode');
        } else {
            console.warn(`[VC] Could not find parent row with class 'countRow' for record ${countRecordId}`);
        }
    } else {
        console.warn(`[VC] Could not find element with data-countrecord-id=${countRecordId}`);
    }

    let convertedQuantity = totalQuantity;
    
    // Return the original quantity if no item code found
    if (!itemCode) {
        return convertedQuantity;
    }

    // Create a unique cache key
    const cacheKey = `${itemCode}-${recordType}`;

    // Check if the data is already in the cache
    if (conversionCache[cacheKey]) {
        const cachedResponse = conversionCache[cacheKey];
        
        if (cachedResponse && cachedResponse.standard_uom) { // Check for minimal necessary data
            // Perform conversion logic using cachedResponse, even if counting_unit is null
            if (cachedResponse.counting_unit && cachedResponse.standard_uom && cachedResponse.counting_unit !== cachedResponse.standard_uom) {
                const isLbToGal = cachedResponse.counting_unit === 'LB' && cachedResponse.standard_uom === 'GAL';
                const isGalToLb = cachedResponse.counting_unit === 'GAL' && cachedResponse.standard_uom === 'LB';
                if (cachedResponse.ship_weight) {
                    const shipWeight = parseFloat(cachedResponse.ship_weight) || 1;
                    if (isLbToGal) {
                        convertedQuantity = totalQuantity / shipWeight;
                    } else if (isGalToLb) {
                        convertedQuantity = totalQuantity * shipWeight;
                    }
                }
            }
        }
        return convertedQuantity;
    }
    // Make the AJAX call synchronous to ensure we get the result before continuing
    
    
    try {
        $.ajax({
            url: `/core/get-json-counting-unit?itemCode=${itemCode}&record_type=${recordType}/`,
            type: 'GET',
            dataType: 'json',
            async: false, // Make synchronous to ensure we get the result
            success: function(response) {
                
                // Always cache the response to avoid re-fetching, even if some fields are null.
                conversionCache[cacheKey] = {
                    counting_unit: response.counting_unit,
                    standard_uom: response.standard_uom,
                    ship_weight: response.ship_weight,
                    retrieved_at: new Date().toISOString() // Optional: to know when it was cached
                };

                if (response && response.counting_unit && response.standard_uom) {
                    const countingUnitMatches = response.counting_unit === response.standard_uom;

                    // Modify totalQuantity based on the response
                    if (!countingUnitMatches) {
                        const isLbToGal = response.counting_unit === 'LB' && response.standard_uom === 'GAL';
                        const isGalToLb = response.counting_unit === 'GAL' && response.standard_uom === 'LB';
                        // If counting unit doesn't match standard UOM, adjust by ship weight
                        if (response.ship_weight) {
                            // Convert using ship weight as the conversion factor
                            const shipWeight = parseFloat(response.ship_weight) || 1;
                            
                            if (isLbToGal) {
                                // Convert from pounds to gallons (divide by ship weight)
                                convertedQuantity = totalQuantity/shipWeight;
                            } else if (isGalToLb) {
                                // Convert from gallons to pounds (multiply by ship weight)
                                convertedQuantity = totalQuantity*shipWeight;
                            }
                        }
                    }
                }
            },
            error: function(xhr, status, error) {
                // Error handling silently fails
            }
        });
    } catch (e) {
        // Exception handling silently fails
    }
    return convertedQuantity;
}

export function calculateVarianceAndCount(countRecordId) {
    
    // SECTION 1: Input gathering and setup
    const recordType = $(`span[data-countrecord-id="${countRecordId}"].record-type`).text().trim() || getURLParameter('recordType');
    const shouldSubtractTare = (recordType === 'blendcomponent');
    let totalQuantity = 0;
    let convertedQuantity = 0;
    
    // SECTION 2: Container quantity calculation using direct container data
    try {
        // First, try to get the containers from the global containerManager instance
        if (!window.containerManager && window.countListPage && window.countListPage.containerManager) {
            window.containerManager = window.countListPage.containerManager;
        }
        // Directly gather container data rather than using DOM selectors
        let containers = [];
        if (window.containerManager && typeof window.containerManager._gatherContainerData === 'function') {
            containers = window.containerManager._gatherContainerData(countRecordId);
            
            containers.forEach((container, idx) => {
                try {
                    const containerRow = $(`.containerRow[data-container-id="${container.container_id}"]`);
                    if (containerRow.length > 0) {
                        const domNetChecked = containerRow.find('input.container_net_measurement').is(':checked');
                        const domTareDisabled = containerRow.find('input.tare_weight').prop('disabled');
                    }
                } catch (e) {
                    console.error(`[VC-CRITICAL] Error checking DOM state:`, e);
                }
            });
        } else {
            console.error(`[VC-CRITICAL] Container Manager not available`);
        }
        
        // Now process the containers to calculate the total
        if (containers.length > 0) {
            let runningTotal = 0;
            const containerQuantityElement = $(`#containersModalLabel${countRecordId}`).find('p.containerQuantity');
            containerQuantityElement.text(` ${containers.length}`);
            containers.forEach((container, index) => {
                // Parse the quantity as a float, defaulting to 0 if invalid
                let quantity = parseFloat(container.container_quantity) || 0;
                let originalQuantity = quantity;
                let tareToSubtract = 0; // For logging
                
                // For blendcomponent records, handle tare weight subtraction
                if (shouldSubtractTare) {
                    
                    // Check if this is a NET measurement (tare already accounted for)
                    // Try multiple detection approaches
                    const isNetMeasurement = (
                        container.net_measurement === true || 
                        container.net_measurement === 'true' || 
                        container.net_measurement === 1
                    );  
                    
                    if (!isNetMeasurement) {
                        // Subtract tare weight for gross measurements
                        const tareWeight = parseFloat(container.tare_weight) || 0;
                        quantity = quantity - tareWeight;
                        tareToSubtract = tareWeight; // For logging
                    } 
                }
                runningTotal += quantity;
            });
            
            totalQuantity += runningTotal;
            convertedQuantity = _convertQuantityIfNeeded(countRecordId, runningTotal, recordType);

        } else {
            const containerQuantityElement = $(`#containersModalLabel${countRecordId}`).find('p.containerQuantity');
            containerQuantityElement.text(` ${containers.length}`);
        }
    } catch (error) {
        console.error(`[VC-CRITICAL] Error during container calculation: ${error.message}`, error);
    }
    
    // SECTION 3: Update UI with calculated values
    try {
        // Ensure totalQuantity is a number before using toFixed
        if (typeof totalQuantity !== 'number') {
            console.error(`[VC-CRITICAL] totalQuantity is not a number: ${typeof totalQuantity}, value: ${totalQuantity}`);
            totalQuantity = parseFloat(totalQuantity) || 0;
        }
        
        // Format values for display
        const formattedTotal = totalQuantity.toFixed(4);
        $(`input.counted_quantity[data-countrecord-id="${countRecordId}"]`).val(formattedTotal);

        const formattedConversion = convertedQuantity.toFixed(4);
        $(`td.tbl-cell-sage_converted_quantity[data-countrecord-id="${countRecordId}"]`).text(formattedConversion);

        // Update the sage converted quantity display if it exists
        if (convertedQuantity !== undefined && convertedQuantity !== null) {
            const formattedConvertedQuantity = typeof convertedQuantity === 'number' ? 
                convertedQuantity.toFixed(4) : 
                (parseFloat(convertedQuantity) || 0).toFixed(4);
                
            // Update the sage converted quantity cell
            $(`td.tbl-cell-sage-quantity[data-countrecord-id="${countRecordId}"]`).text(formattedConvertedQuantity);
        }
        
        // Calculate variance
        const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text() || '0');
        const variance = totalQuantity - expectedQuantity;
        const formattedVariance = variance.toFixed(4);
        
        // Update variance field
        $(`td.tbl-cell-variance[data-countrecord-id="${countRecordId}"]`).text(formattedVariance);
    } catch (error) {
        console.error(`[VC-CRITICAL] Error updating UI: ${error.message}`, error);
    }
    
    // SECTION 4: Send WebSocket update
    try {
        if (window.thisCountListWebSocket) {
            const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text() || '0');
            const variance = totalQuantity - expectedQuantity;
            
            // Ensure totalQuantity is a number before using toFixed
            if (typeof totalQuantity !== 'number') {
                console.error(`[VC-CRITICAL] totalQuantity is not a number before WebSocket update: ${typeof totalQuantity}`);
                totalQuantity = parseFloat(totalQuantity) || 0;
            }
            
            // Get containers for a complete update
            let containers = [];
            if (window.containerManager && typeof window.containerManager._gatherContainerData === 'function') {
                containers = window.containerManager._gatherContainerData(countRecordId);
            } else {
                // Fallback manual container gathering
                const containerTable = $(`table[data-countrecord-id="${countRecordId}"].container-table`);
                containerTable.find('tr.containerRow').each(function() {
                    const containerData = {
                        'container_id': $(this).find('input.container_id').val(),
                        'container_quantity': $(this).find('input.container_quantity').val(),
                        'container_type': $(this).find('select.container_type').val(),
                        'tare_weight': $(this).find('input.tare_weight').val(),
                        'net_measurement': $(this).find('input.container_net_measurement').is(':checked'),
                    };
                    containers.push(containerData);
                });
            }

            // SPECIAL CHECKING: Verify if any containers have NET measurement enabled
            let hasNetMeasurements = false;
            let totalTareWeight = 0;
            containers.forEach((container, idx) => {
                // Double check NET measurement state for WebSocket update
                if (container.net_measurement === true || container.net_measurement === 'true' || container.net_measurement === 1) {
                    hasNetMeasurements = true;
                }
                const tareWeight = parseFloat(container.tare_weight) || 0;
                totalTareWeight += tareWeight;
            });
            

        }
    } catch (wsError) {
        console.error(`[VC-CRITICAL] Error sending WebSocket update:`, wsError);
    }
    
    return totalQuantity; // Return the calculated value for potential use elsewhere
}

/**
 * Handles the relationship between net measurement checkboxes and tare weight fields
 * If the checkbox is checked, disables the tare weight field and clears its value
 * If the checkbox is unchecked, enables the tare weight field and sets appropriate tare weight
 * 
 * @param {jQuery|string} selector - jQuery selector or object for the container(s) whose checkboxes need to be processed
 */
export function initializeNetMeasurementCheckboxes(selector) {
    // If a string selector is passed, convert to jQuery object
    const elements = typeof selector === 'string' ? $(selector) : selector;
    
    elements.find('.container_net_measurement').each(function() {
        const checkboxElement = $(this);
        const row = checkboxElement.closest('tr');
        // Use the correct selector pattern for the tare weight input
        const tareWeightInput = row.find('input.tare_weight');
        
        // Only add event handler if not already bound
        if (!checkboxElement.data('event-bound')) {
            checkboxElement.on('change', function() {
                if (checkboxElement.is(':checked')) {
                    // Set to zero and disable when checked
                    tareWeightInput.val('0').prop('disabled', true);
                } else {
                    // Re-enable when unchecked
                    tareWeightInput.prop('disabled', false);
                    
                    // Get container manager instance if available
                    let containerManager = null;
                    try {
                        containerManager = window.countListPage && window.countListPage.containerManager;
                    } catch(e) {
                        // No container manager available
                        console.log(`[VC-CRITICAL] No container manager available: oh no oh no oh no no no`, e);
                    }
                    
                    if (containerManager) {
                        const containerType = row.find('select.container_type').val();
                        const recordType = getURLParameter('recordType');
                        const tareWeight = containerManager._getTareWeightForContainerType(containerType, recordType);
                        tareWeightInput.val(tareWeight);
                    } else {
                        // Fallback for legacy code paths
                        const containerType = row.find('select.container_type').val();
                        let tareWeight = 0;
                        
                        // Determine tare weight based on container type
                        const recordType = getURLParameter('recordType');
                        if (recordType === 'blendcomponent') {
                            if (containerType === "275gal tote") tareWeight = 125;
                            else if (containerType === "poly drum") tareWeight = 22;
                            else if (containerType === "regular metal drum") tareWeight = 37;
                            else if (containerType === "large poly tote") tareWeight = 0;
                            else if (containerType === "stainless steel tote") tareWeight = 0;
                            else if (containerType === "300gal tote") tareWeight = 150;
                            else if (containerType === "small poly drum") tareWeight = 13;
                            else if (containerType === "enzyme metal drum") tareWeight = 50;
                            else if (containerType === "plastic pail") tareWeight = 3;
                            else if (containerType === "metal pail") tareWeight = 4;
                            else if (containerType === "cardboard box") tareWeight = 2;
                            else if (containerType === "gallon jug") tareWeight = 1;
                            else if (containerType === "storage tank") tareWeight = 0;
                            else if (containerType === "pallet") tareWeight = 45;
                            else if (containerType === "powderbag") tareWeight = 0;
                        }

                        tareWeightInput.val(tareWeight);
                    }
                }
                
                // Calculate variance and update count if we can find the record ID
                const recordId = row.find('[data-countrecord-id]').first().attr('data-countrecord-id');
                if (recordId) {
                    calculateVarianceAndCount(recordId);
                }
            });

            // Initial setup based on current state
            if (checkboxElement.is(':checked')) {
                tareWeightInput.val('0').prop('disabled', true);
            }

            checkboxElement.data('event-bound', true);
        }
    });
}

/**
 * Container Manager Class - Manages container data and UI interaction
 * Handles data retrieval, UI rendering, and event binding for container rows
 */
export class ContainerManager {
    constructor(countListWebSocket) {
        this.webSocket = countListWebSocket;
        this.cachedContainers = new Map(); // Store container data by countRecordId
    }
    
    /**
     * Gets container data for a count record, either from cache or from the server
     * @param {string|number} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record (blend, blendcomponent, etc.)
     * @param {boolean} forceRefresh - Whether to force a refresh from the server
     * @returns {Array} - Array of container objects
     */
    getContainers(countRecordId, recordType, forceRefresh = false) {
        // Check cache first if not forcing refresh
        if (!forceRefresh && this.cachedContainers.has(countRecordId)) {
            // CM Log
            return this.cachedContainers.get(countRecordId);
        }
        
        // Get from server
        let containers = [];
                $.ajax({
            url: `/core/get-json-containers-from-count?countRecordId=${countRecordId}&recordType=${recordType}`,
            async: false, // Critical: This must be synchronous to ensure we get the data before returning
                    dataType: 'json',
                    success: function(data) {
                containers = data;
            },
            error: function(xhr, status, error) {
                console.error(`❌ Error fetching containers from server: ${error}`);
            }
        });
        
        // Update cache with the latest data from server
        this.cachedContainers.set(countRecordId, containers);
        
        return containers;
    }
    
    /**
     * Renders container rows in a container table body
     * @param {string} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record
     * @param {jQuery|HTMLElement} containerTableBody - The container table body element
     */
    renderContainerRows(countRecordId, recordType, containerTableBody, options = {}) {
        // Ensure containerTableBody is a jQuery object
        containerTableBody = $(containerTableBody);
        
        // Get container data, either from cache or server
        const containers = this.getContainers(countRecordId, recordType);
        
        // Extract options
        const isDeleteOperation = options.isDeleteOperation || false;
        
        // Clear existing rows
        containerTableBody.empty();
        
        // Update container quantity display - Fixed to show actual count
        const containerCount = containers.length > 0 ? containers.length : 0;
        $(`#containersModalLabel${countRecordId}`).find('.containerQuantity').text(containerCount);
        
        if (containers.length === 0 && !isDeleteOperation) {
            // Only add an empty container row if:
            // 1. There are no containers AND
            // 2. This is NOT a delete operation (if it's a delete, respect the empty state)
            containerTableBody.append(this._createEmptyContainerRow(countRecordId, recordType));
        } else {
            // Render each container from the server data
            containers.forEach((container) => {
                // IMPORTANT: Use data directly from the server, preserving all values exactly as they were saved
                containerTableBody.append(this._createContainerRow(container, countRecordId, recordType));
            });
        }
        
        // Initialize checkbox states
        initializeNetMeasurementCheckboxes(containerTableBody);
        
        // Set up event handlers for the container rows
        this._setupEventHandlers(containerTableBody, countRecordId, recordType);
    }

    /**
     * Creates HTML for an empty container row
     * @private
     */
    _createEmptyContainerRow(countRecordId, recordType) {
        // Determine the default container type and its associated tare weight
        const defaultContainerType = "275gal tote";
        const defaultTareWeight = this._getTareWeightForContainerType(defaultContainerType, recordType);
        
        // Generate a unique ID for the empty container (different from 0)
        const uniqueId = Date.now() + "_empty";
        
        return `<tr data-container-id="${uniqueId}" data-countrecord-id="${countRecordId}" class="containerRow">
                        <td class='container_id' style="display:none;">
                        <input type="text" class="form-control container_id" data-countrecord-id="${countRecordId}" value="${uniqueId}" data-container-id="${uniqueId}">
                        </td>
                    <td class='quantity'><input type="number" class="form-control container_quantity decimal-input" data-countrecord-id="${countRecordId}" value="" data-container-id="${uniqueId}"></td>
                        <td class='container_type'>
                        <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="${uniqueId}">
                            <option value="275gal tote" selected data-countrecord-id="${countRecordId}">275gal tote</option>
                                <option value="poly drum" data-countrecord-id="${countRecordId}">Poly Drum</option>
                                <option value="regular metal drum" data-countrecord-id="${countRecordId}">Regular Metal Drum</option>
                                <option value="large poly tote" data-countrecord-id="${countRecordId}">Large Poly Tote</option>
                                <option value="stainless steel tote" data-countrecord-id="${countRecordId}">Stainless Steel Tote</option>
                                <option value="pallet" data-countrecord-id="${countRecordId}">Pallet</option>
                                <option value="powderbag" data-countrecord-id="${countRecordId}">Powder Bag</option>
                                <option value="300gal tote" data-countrecord-id="${countRecordId}">300gal Tote</option>
                                <option value="small poly drum" data-countrecord-id="${countRecordId}">Small Poly Drum</option>
                                <option value="enzyme metal drum" data-countrecord-id="${countRecordId}">Enzyme Metal Drum</option>
                                <option value="plastic pail" data-countrecord-id="${countRecordId}">Plastic Pail</option>
                                <option value="metal pail" data-countrecord-id="${countRecordId}">Metal Pail</option>
                                <option value="cardboard box" data-countrecord-id="${countRecordId}">Cardboard Box</option>
                                <option value="gallon jug" data-countrecord-id="${countRecordId}">Gallon Jug</option>
                                <option value="storage tank" data-countrecord-id="${countRecordId}">Storage Tank</option>
                            </select>
                        </td>
                        <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
                        <input type="number" class="form-control tare_weight decimal-input" data-countrecord-id="${countRecordId}" value="${defaultTareWeight}" data-container-id="${uniqueId}">
                        </td>
                        <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                        <input type="checkbox" class="container_net_measurement" data-countrecord-id="${countRecordId}" data-container-id="${uniqueId}">
                        </td>
                    <td class="actions-cell">
                        <div class="actions-cell-content-wrapper">
                            <div class="action-button-wrapper">
                                <span class="action-button-label">Print</span>
                                <i class="fa fa-print container-print-button" data-countrecord-id="${countRecordId}" data-container-id="${uniqueId}"></i>
                            </div>
                            <div class="action-button-wrapper">
                                <span class="action-button-label">Delete</span>
                                <i class="fa-solid fa-trash-alt row-clear" data-countrecord-id="${countRecordId}" data-container-id="${uniqueId}"></i>
                            </div>
                        </div>
                    </td>
                </tr>`;
    }
    
    /**
     * Creates HTML for a container row with data
     * @private
     */
    _createContainerRow(container, countRecordId, recordType) {
        return `<tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
                            <td class='container_id' style="display:none;">
                            <input type="text" class="form-control container_id" data-countrecord-id="${countRecordId}" value="${container.container_id}" data-container-id="${container.container_id}">
                            </td>
                            <td class='quantity'>
                                <input type="number" class="form-control container_quantity decimal-input" data-countrecord-id="${countRecordId}" value="${container.container_quantity || ''}" data-container-id="${container.container_id}">
                            </td>
                            <td class='container_type'>
                                <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
                                    <option value="275gal tote" ${container.container_type === '275gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">275gal tote</option>
                                    <option value="poly drum" ${container.container_type === 'poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Poly Drum</option>
                                    <option value="regular metal drum" ${container.container_type === 'regular metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Regular Metal Drum</option>
                                    <option value="large poly tote" ${container.container_type === 'large poly tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Large Poly Tote</option>
                                    <option value="stainless steel tote" ${container.container_type === 'stainless steel tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Stainless Steel Tote</option>
                                    <option value="pallet" ${container.container_type === 'pallet' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Pallet</option>
                                    <option value="powderbag" ${container.container_type === 'powderbag' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Powder Bag</option>
                                    <option value="300gal tote" ${container.container_type === '300gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">300gal Tote</option>
                                    <option value="small poly drum" ${container.container_type === 'small poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Small Poly Drum</option>
                                    <option value="enzyme metal drum" ${container.container_type === 'enzyme metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Enzyme Metal Drum</option>
                                    <option value="plastic pail" ${container.container_type === 'plastic pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Plastic Pail</option>
                                    <option value="metal pail" ${container.container_type === 'metal pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Metal Pail</option>
                                    <option value="cardboard box" ${container.container_type === 'cardboard box' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Cardboard Box</option>
                                    <option value="gallon jug" ${container.container_type === 'gallon jug' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Gallon Jug</option>
                                    <option value="storage tank" ${container.container_type === 'storage tank' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Storage Tank</option>
                                </select>
                            </td>
                            <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
                                <input type="number" class="form-control tare_weight decimal-input" data-countrecord-id="${countRecordId}" value="${container.tare_weight || ''}" data-container-id="${container.container_id}">
                            </td>
                            <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                <input type="checkbox" class="container_net_measurement" ${container.net_measurement === true || container.net_measurement === "true" ? 'checked' : ''} data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
                            </td>
                            <td class="actions-cell">
                                <div class="actions-cell-content-wrapper">
                                    <div class="action-button-wrapper">
                                        <span class="action-button-label">Print</span>
                                        <i class="fa fa-print container-print-button" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i>
                                    </div>
                                    <div class="action-button-wrapper">
                                        <span class="action-button-label">Delete</span>
                                        <i class="fa-solid fa-trash-alt row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i>
                                    </div>
                                </div>
                            </td>
        </tr>`;
    }
    
    /**
     * Sets up event handlers for a container table
     * @private
     */
    _setupEventHandlers(containerTableBody, countRecordId, recordType) {
        const self = this; // Store reference to ContainerManager for event callbacks
        
        // Set up event handlers for each container row
        $(containerTableBody).find('tr.containerRow').each(function() {
            // Use our shared row event handler setup method for consistency
            self._setupRowEventHandlers($(this), countRecordId, recordType);
        });
        
        // Add container row handler - IMPORTANT: We need to find this button outside the table body
        const $addButton = $(`.add-container-row[data-countrecord-id="${countRecordId}"]`);
        
        // Ensure we don't have multiple bindings - off before on
        $addButton.off('click').on('click', function() {
            self._handleAddContainerRow($(this), countRecordId, recordType);
        });
        
        // Set up multi-container print button handler
        const $multiPrintButton = $(`.multi-container-print-button[data-countrecord-id="${countRecordId}"]`);
        $multiPrintButton.off('click').on('click', function() {
            self._handleMultiContainerPrint(countRecordId, recordType);
        });
    }
    
    /**
     * Handles adding a new container row when the add button is clicked
     * @param {jQuery} buttonElement - The button element that was clicked
     * @param {string} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record
     * @private
     */
    _handleAddContainerRow(buttonElement, countRecordId, recordType) {
        const self = this;
        console.log(`[CM] Attempting to add container row for record ID: ${countRecordId}, recordType: ${recordType}`); // CM Log
        
        // Ensure we have the correct record ID
        const recordId = buttonElement.attr('data-countrecord-id') || countRecordId;
        if (!recordId) {
            console.error("Cannot add container row: Missing record ID");
            return;
        }
        
        // Find the container table body for this record
        const containerTableBody = $(`table.container-table[data-countrecord-id="${recordId}"] tbody.containerTbody`);
        if (containerTableBody.length === 0) {
            console.error(`Cannot find container table body for record ID ${recordId}`);
            return;
        }
        // Get the last row in the container table
        const lastRow = containerTableBody.find('tr:last');
        if (lastRow.length === 0) {
            console.error(`Cannot find last row in container table for record ID ${recordId}`);
            return;
        }
        
        // Clone the last row
        const newRow = lastRow.clone();
        
        // Reset input values in the new row (except for container type and tare weight)
        newRow.find('input.container_quantity').val('');
        newRow.find('input.container_net_measurement').prop('checked', false);
        
        // Set a unique container ID for the new row
        const newContainerId = this._generateNewContainerId(containerTableBody);
        newRow.attr('data-container-id', newContainerId);
        
        // Update all input and select elements with the new container ID
        newRow.find('input, select').each(function() {
            $(this).attr('data-container-id', newContainerId);
        });
        
        // Also update the container_id input value
        newRow.find('input.container_id').val(newContainerId);
        
        // Update the delete and print buttons with the new container ID
        newRow.find('.fa-trash-alt.row-clear').attr('data-container-id', newContainerId);
        newRow.find('.fa.fa-print.container-print-button').attr('data-container-id', newContainerId);
        
        // Set the appropriate tare weight based on the selected container type
        const selectedContainerType = newRow.find('select.container_type').val();
        const tareWeight = this._getTareWeightForContainerType(selectedContainerType, recordType);
        
        // Update the tare weight input
        newRow.find('input.tare_weight').val(tareWeight);
        
        // Setup event handlers for the new row using the same single-vector pattern
        this._setupRowEventHandlers(newRow, countRecordId, recordType);
        
        // Add the new row to the container table body
        containerTableBody.append(newRow);
        
        // Update container count display after adding
        const currentCount = containerTableBody.find('tr.containerRow').length;
        $(`#containersModalLabel${countRecordId}`).find('.containerQuantity').text(currentCount);
        
        // CRITICAL FIX: Pre-calculate all values before sending a single update
        console.log(`[CM] Calling preCalculateValues before sending update (add action) for record ID: ${recordId}`); // CM Log
        this._preCalculateValues(countRecordId, 'add');
        
        // Send update to server
        this._sendUpdateToServer(countRecordId, newContainerId, 'add');
    }
    
    /**
     * Updates a container table when data changes
     * @param {string|number} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record
     * @param {string|number} containerId - The ID of the container that was updated
     */
    updateContainerTable(countRecordId, recordType, containerId) {
        // Force refresh from server
        this.getContainers(countRecordId, recordType, true);
        
        // Get the container table
        const containerTableBody = $(`#countsTable tbody tr[data-countrecord-id=${countRecordId}]`).find('table.container-table');
        
        // Render the updated table
        this.renderContainerRows(countRecordId, recordType, containerTableBody);
        
        // Focus on the updated container
        const thisContainerRow = $(`tr[data-countrecord-id="${countRecordId}"][data-container-id="${containerId}"]`);
        const quantityInput = thisContainerRow.find('input.container_quantity');
        quantityInput.on('focus', function() {
            let value = $(this).val();
            setTimeout(() => {
                if ($(this).attr('type') === 'number') {
                    $(this).val(null).val(value); // Temporarily set to null and back to value to move cursor
                } else if ($(this).attr('type') === 'text') {
                    let valueLength = value.length;
                    this.setSelectionRange(valueLength, valueLength); // For text inputs, use setSelectionRange
                }
            }, 0); // Delay of 0ms to ensure it runs after the focus event
        });
        quantityInput.focus();
    }
    
    /**
     * Initializes container fields for all count records in the table
     * To be called on page load
     * @param {Object} countListWebSocket - Optional WebSocket reference to use for updating
     */
    initializeAllContainerFields(countListWebSocket) {
        const self = this;
        
        // If a WebSocket is provided, update our reference
        if (countListWebSocket) {
            this.webSocket = countListWebSocket;
        }
        
        // Process each count record
        $('#countsTable tbody tr.countRow').each(function() {
            const containerTableBody = $(this).find('tbody.containerTbody');
            const countRecordId = $(this).attr('data-countrecord-id');
            const recordType = getURLParameter('recordType');
            
            // Render container rows for this count record
            self.renderContainerRows(countRecordId, recordType, containerTableBody);
        });
        
        // Do one final pass to ensure all add-container-row buttons are properly bound
        // This ensures buttons outside specific container tables are properly handled
        $('.add-container-row').each(function() {
            // REMOVED: Redundant binding that causes double-firing
            // Each button should already be bound by _setupEventHandlers
            // This was causing duplicate event registrations
            
            // Verify button has proper data attribute
            const countRecordId = $(this).attr('data-countrecord-id');
            if (!countRecordId) {
                console.warn(`Found add-container-row button without data-countrecord-id attribute`);
            }
        });
        
        // Initialize all tare weight fields based on checkbox states
        initializeNetMeasurementCheckboxes('#countsTable');
    }

    /**
     * Generates a new container ID based on the highest existing ID
     * @param {jQuery} containerTableBody - The container table body to check for existing IDs
     * @returns {number} - A new unique container ID
     * @private
     */
    _generateNewContainerId(containerTableBody) {
        let highestId = 0;
        
        // Find all existing container IDs and determine the highest
        containerTableBody.find('tr').each(function() {
            // Extract the container ID from data attribute
            const containerId = parseInt($(this).attr('data-container-id')) || 0;
            if (containerId > highestId) {
                highestId = containerId;
            }
        });
        
        // Return the next available ID (simple increment)
        return highestId + 1;
    }
    
    /**
     * Sends an update to the server for a container change
     * @param {string} recordId - The ID of the count record
     * @param {string} containerId - The ID of the container
     * @param {string} action - The type of action (update, delete)
     * @private
     */
    _sendUpdateToServer(recordId, containerId, action) {
        try {  
            // Special handling for deletions - if deleting, remove this container from the containers array
            let containers = this._gatherContainerData(recordId);
            
            if (action === 'delete') {
                // Filter out the container being deleted by ID
                const originalLength = containers.length;
                
                containers = containers.filter(container => {
                    // Convert both to strings for reliable comparison
                    const containerIdStr = String(container.container_id);
                    const targetIdStr = String(containerId);
                    return containerIdStr !== targetIdStr;
                });
                
                // If we're deleting the last container, add an empty one to maintain UI structure
                if (containers.length === 0) {
                    containers.push({
                        'container_id': String(Date.now()) + "_empty",
                        'container_quantity': '',
                        'container_type': '275gal tote',
                        'tare_weight': this._getTareWeightForContainerType('275gal tote', getURLParameter("recordType") || 'blendcomponent'),
                        'net_measurement': false
                    });
                }
            }
            
            // Get current values from the UI AFTER calculation was performed
            const countedQuantityValue = $(`input[data-countrecord-id="${recordId}"].counted_quantity`).val();
            const varianceValue = $(`td[data-countrecord-id="${recordId}"].tbl-cell-variance`).text();
            
            // Get the sage converted quantity value from the input field
            const sageConvertedQuantityValue = $(`td.tbl-cell-sage_converted_quantity[data-countrecord-id="${recordId}"]`).text()
            console.log(sageConvertedQuantityValue)

            // Get other record data
            const recordType = getURLParameter("recordType") || 'blendcomponent';
            
            const recordData = {
                'counted_quantity': countedQuantityValue,
                'expected_quantity': $(`span[data-countrecord-id="${recordId}"].expected-quantity-span`).text().trim(),
                'variance': varianceValue,
                'sage_converted_quantity': sageConvertedQuantityValue,
                'counted_date': $(`td[data-countrecord-id="${recordId}"].tbl-cell-counted_date`).text() || new Date().toISOString().split('T')[0],
                'counted': $(`input[data-countrecord-id="${recordId}"].counted-input`).prop("checked"),
                'comment': $(`textarea[data-countrecord-id="${recordId}"].comment`).val() || '',
                'location': $(`select[data-countrecord-id="${recordId}"].location-selector`).val() || '',
                'containers': containers,
                'containerId': containerId,
                'record_type': recordType,
                'action_type': action, // Add action type to help server understand intent
                'should_subtract_tare': recordType === 'blendcomponent' // Explicit flag for server-side logic
            };
            
            // Update the cache immediately with the latest container data
            this.cachedContainers.set(recordId, containers);
            
            // Send update through WebSocket
            if (this.webSocket) {
                this.webSocket.updateCount(recordId, recordType, recordData);
            } else if (window.thisCountListWebSocket) {
                window.thisCountListWebSocket.updateCount(recordId, recordType, recordData);
            } else {
                // Fallback to original method if WebSocket is not available
                console.warn(`⚠️ No WebSocket reference available, oh no!`);
                const eventTarget = $(`[data-countrecord-id="${recordId}"]`).first();
                if (typeof sendCountRecordChange === 'function') {
                    sendCountRecordChange(eventTarget, this.webSocket, containerId);
                } else {
                    console.error(`❌ sendCountRecordChange function not found, update may not be saved!`);
                }
            }
                        
        } catch (error) {
            console.error("Failed to send update to server:", error);
        }
    }
    
    /**
     * Gathers container data for a specific count record
     * @param {string} recordId - The ID of the count record
     * @returns {Array} - Array of container data objects
     * @private
     */
    _gatherContainerData(recordId) {
        const containers = [];
        const containerTable = $(`table[data-countrecord-id="${recordId}"].container-table`);
        
        containerTable.find('tr.containerRow').each(function(index) {
            const $row = $(this);
            const netCheckbox = $row.find('input.container_net_measurement');
            const isNetChecked = netCheckbox.is(':checked');
            const tareInput = $row.find('input.tare_weight');
            const tareValue = tareInput.val();
            const tareDisabled = tareInput.prop('disabled');

            const containerData = {
                'container_id': $row.find('input.container_id').val(),
                'container_quantity': $row.find('input.container_quantity').val(),
                'container_type': $row.find('select.container_type').val(),
                'tare_weight': tareValue,
                'net_measurement': isNetChecked, // Store as boolean
            };
            containers.push(containerData);
        });
        
        return containers;
    }

    _getTareWeightForContainerType(containerType, recordType) {
        // Only set specific tare weights for blendcomponent record type
        if (recordType !== 'blendcomponent') {
            return 0;
        }
        
        // Map of container types to their tare weights
        const tareWeightMap = {
            "275gal tote": 125,
            "poly drum": 22,
            "regular metal drum": 37,
            "300gal tote": 150,
            "small poly drum": 13,
            "enzyme metal drum": 50,
            "plastic pail": 3,
            "metal pail": 4,
            "cardboard box": 2,
            "gallon jug": 1,
            "large poly tote": 0,
            "stainless steel tote": 0,
            "storage tank": 0
        };
        
        // Return the tare weight for the container type, or 0 if not found
        return tareWeightMap[containerType] || 0;
    }

    _preCalculateValues(countRecordId, action = 'update') {
        try {
            console.log(`[CM-PRECALC] Starting preCalculation for ${countRecordId}, action: ${action}`);
            // CRITICAL FIX: Call the enhanced calculateVarianceAndCount function
            // This ensures tare weights are properly processed
            const totalQuantity = calculateVarianceAndCount(countRecordId);
            
            // Format the calculated values consistently for return
            const formattedTotal = parseFloat(totalQuantity).toFixed(4);
            
            // Get the expected quantity and calculate variance
            const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text()) || 0;
            const variance = totalQuantity - expectedQuantity;
            const formattedVariance = variance.toFixed(4);
            
            // Update the date automatically for convenience
            const today = new Date();
            const formattedDate = today.toISOString().split('T')[0];
            $(`td[data-countrecord-id="${countRecordId}"]`).find("input[name*='counted_date']").val(formattedDate);
            
            console.log(`[CM-PRECALC] Pre-calculation successful for ${countRecordId}. Total: ${formattedTotal}, Variance: ${formattedVariance}`);
            return {
                totalQuantity: formattedTotal,
                variance: formattedVariance
            };
        } catch (error) {
            console.error(`Error in pre-calculation (${action}):`, error);
            
            // Emergency fallback to ensure we don't break the UI
            console.log(`[PreCalculate] ⚠️ Emergency fallback calculation triggered`);
            calculateVarianceAndCount(countRecordId);
            
            return null;
        }
    }

    /**
     * Sets up event handlers for a single container row
     * Uses the same single-vector pattern for all events
     * @param {jQuery} row - The row element to set up handlers for
     * @param {string} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record
     * @private
     */
    _setupRowEventHandlers(row, countRecordId, recordType) {
        const self = this;
        const containerId = row.attr('data-container-id');
        
        // Container type change handler
        row.find('select.container_type').off('change').on('change', function() {
            // Get the selected container type
            const containerType = $(this).val();
            
            // Update tare weight based on container type
            const tareWeight = self._getTareWeightForContainerType(containerType, recordType);
            row.find('input.tare_weight').val(tareWeight);
            
            // Pre-calculate all values
            self._preCalculateValues(countRecordId, 'update');
            
            // Send a single update to server
            self._sendUpdateToServer(countRecordId, containerId, 'update');
        });
        
        // Container quantity change handler
        row.find('input.container_quantity').off('input').on('input', function() {
            const $this = $(this);
            
            // Clear any pending updates
            clearTimeout($this.data('debounce-timer'));
            
            // Provide immediate visual feedback
            $this.css('background-color', '#FFFACD');
            
            // Debounce the expensive operations
            $this.data('debounce-timer', setTimeout(function() {
                // Restore background
                $this.css('background-color', '');
                
                // Pre-calculate all values
                self._preCalculateValues(countRecordId, 'update');
                
                // Send a single update to server with a delay of 1500ms - container quantity delay
                self._sendUpdateToServer(countRecordId, containerId, 'update');
            }, 1500));
        });
        
        // NET measurement checkbox change handler
        row.find('.container_net_measurement').off('change').on('change', function() {
            // Find the tare weight input in the same row - using the correct selector
            const tareWeightInput = row.find('input.tare_weight');
            
            if ($(this).is(':checked')) {
                // Set to zero and disable when checked
                tareWeightInput.val('0').prop('disabled', true);
            } else {
                // Re-enable the field and set appropriate tare weight when unchecked
                tareWeightInput.prop('disabled', false);
                const containerType = row.find('select.container_type').val();
                const tareWeight = self._getTareWeightForContainerType(containerType, recordType);
                tareWeightInput.val(tareWeight);
            }
            
            // Pre-calculate all values
            self._preCalculateValues(countRecordId, 'update');
            
            // Send a single update to server
            self._sendUpdateToServer(countRecordId, containerId, 'update');
        });
        
        // Tare weight change handler
        row.find('input.tare_weight').off('input').on('input', function() {
            const $this = $(this);
            
            // Clear any pending updates
            clearTimeout($this.data('debounce-timer'));
            
            // Debounce the expensive operations
            $this.data('debounce-timer', setTimeout(function() {
                // Pre-calculate all values
                self._preCalculateValues(countRecordId, 'update');
                
                // Send a single update to server
                self._sendUpdateToServer(countRecordId, containerId, 'update');
            }, 400));
        });
        
        // Container delete button handler
        row.find('.fa-trash-alt.row-clear').off('click').on('click', function() {
            // Store the row to be removed
            const $rowToRemove = $(this).closest('tr');
            console.log(`[CM] Deleting container row. Record ID: ${countRecordId}, Container ID: ${containerId}`); // CM Log
            
            // Remove the row from the DOM
            $rowToRemove.remove();
            
            // Pre-calculate all values after deletion
            console.log(`[CM] Calling preCalculateValues after deleting container (delete action). Record ID: ${countRecordId}`); // CM Log
            self._preCalculateValues(countRecordId, 'delete');
            
            // Send a single update to server
            self._sendUpdateToServer(countRecordId, containerId, 'delete');
        });
        
        // Container print button handler
        row.find('.fa.fa-print.container-print-button').off('click').on('click', function() {
            self._handleSingleContainerPrint(countRecordId, containerId, recordType);
        });
    }
    
    /**
     * Handles printing a single container label
     * @param {string} countRecordId - The ID of the count record
     * @param {string} containerId - The ID of the container
     * @param {string} recordType - The type of record
     * @private
     */
    _handleSingleContainerPrint(countRecordId, containerId, recordType) {
        // Import the ContainerLabelPrintButton class dynamically
        import('./buttonObjects.js').then(module => {
            const { ContainerLabelPrintButton } = module;
            
            // Create a temporary button element for the print functionality
            const tempButton = document.createElement('button');
            
            // Create and trigger the print button
            const printButton = new ContainerLabelPrintButton(
                tempButton, 
                containerId, 
                countRecordId, 
                recordType, 
                false // Single print, not batch
            );
            
            // Trigger the print directly
            printButton.printSingleContainerLabel();
        }).catch(error => {
            console.error('Error loading ContainerLabelPrintButton:', error);
        });
    }
    
    /**
     * Handles printing all container labels for a count record
     * @param {string} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record
     * @private
     */
    _handleMultiContainerPrint(countRecordId, recordType) {
        // Import the ContainerLabelPrintButton class dynamically
        import('./buttonObjects.js').then(module => {
            const { ContainerLabelPrintButton } = module;
            
            // Create a temporary button element for the print functionality
            const tempButton = document.createElement('button');
            
            // Create and trigger the print button
            const printButton = new ContainerLabelPrintButton(
                tempButton, 
                null, // No specific container ID for batch print
                countRecordId, 
                recordType, 
                true // Batch print
            );
            
            // Trigger the batch print directly
            printButton.printAllContainerLabels();
        }).catch(error => {
            console.error('Error loading ContainerLabelPrintButton:', error);
        });
    }
}

export function sendCountRecordChange(eventTarget, thisCountListWebSocket, containerId) {
    function updateDate(eventTarget){
        let correspondingID = eventTarget.attr('data-countrecord-id');
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        $(`td[data-countrecord-id="${correspondingID}"]`).find("input[name*='counted_date']").val(formattedDate);
    };
    const dataCountRecordId = eventTarget.attr('data-countrecord-id');
    updateDate(eventTarget);
    calculateVarianceAndCount(dataCountRecordId);
    let containers;
    const containerManager = window.countListPage?.containerManager;

    if (containerManager?.cachedContainers?.has(dataCountRecordId)) {
        const cachedContainers = containerManager.cachedContainers.get(dataCountRecordId) || [];
        containers = cachedContainers.map(container => ({ ...container }));
    } else {
        const gatheredContainers = [];
        const thisContainerTable = $(`table[data-countrecord-id="${dataCountRecordId}"].container-table`);

        thisContainerTable.find('tr.containerRow').each(function() {
            const containerData = {
                'container_id': $(this).find(`input.container_id`).val(),
                'container_quantity': $(this).find(`input.container_quantity`).val(),
                'container_type': $(this).find(`select.container_type`).val(),
                'tare_weight': $(this).find(`input.tare_weight`).val(),
                'net_measurement': $(this).find(`input.container_net_measurement`).is(':checked'),
            };
            gatheredContainers.push(containerData);
        });

        if (containerManager?.cachedContainers) {
            containerManager.cachedContainers.set(
                dataCountRecordId,
                gatheredContainers.map(container => ({ ...container }))
            );
        }

        containers = gatheredContainers;
    }

    const recordId = eventTarget.attr("data-countrecord-id");
    const recordType = getURLParameter("recordType");
    const recordData = {
        'counted_quantity': $(`input[data-countrecord-id="${dataCountRecordId}"].counted_quantity`).val(),
        'expected_quantity': $(`span[data-countrecord-id="${dataCountRecordId}"].expected-quantity-span`).text().trim(),
        'variance': $(`td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-variance`).text(),
        'counted_date': $(`td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-counted_date`).text(),
        'counted': $(`input[data-countrecord-id="${dataCountRecordId}"].counted-input`).prop("checked"),
        'comment': $(`textarea[data-countrecord-id="${dataCountRecordId}"].comment`).val() || '',
        'location': $(`select[data-countrecord-id="${dataCountRecordId}"].location-selector`).val(),
        'sage_converted_quantity': $(`td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-sage_converted_quantity`).text(),
        'containers': containers,
        'containerId': containerId,
        'record_type': recordType
    }

    console.log('[VIZIER_DEBUG] Sending update via WebSocket. Record ID:', recordId, 'Record Type:', recordType, 'Data:', JSON.parse(JSON.stringify(recordData)));
    thisCountListWebSocket.updateCount(recordId, recordType, recordData);
};

export function updateCheckBoxCellColors() {
    $('#countsTable tbody tr td.tbl-cell-counted').each(function() {
        let checked = $(this).find('input[type="checkbox"]').is(':checked');
        if (checked) {
            $(this).removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
        } else {
            $(this).removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
        }
    });
}

export class CountListPage {
    constructor(thisCountListWebSocket, thisCountContainerModal) {
        try {
            // Store WebSocket reference
            this.webSocket = thisCountListWebSocket;
            
            // Create a container manager instance
            this.containerManager = new ContainerManager(thisCountListWebSocket);
            
            // Expose the container manager globally for use by other functions
            window.countListPage = this;
            
            // Initialize the page
            this.containerManager.initializeAllContainerFields(thisCountListWebSocket);
            this.setUpEventListeners(thisCountListWebSocket, thisCountContainerModal);
            updateCheckBoxCellColors();
            this.setupLabelLinks();
            this.setUpMutationObservers(thisCountListWebSocket);

            this.initializeMobileCardToggles();

        } catch(err) {
            console.error(err.message);
        };
    };

    /**
     * Creates a new count record row using proper templating
     * @param {string|number} recordId - The ID of the count record
     * @param {Object} data - The data for the new row
     * @param {Object} options - Additional options
     * @returns {HTMLElement} - The created row element
     */
    createCountRecordRow(recordId, data, options = {}) {
        console.log(`🧪 Creating template row for record ID ${recordId}`);
        
        // Get options or default values
        const recordType = options.recordType || getURLParameter('recordType') || '';
        const disableLabelLinks = options.disableLabelLinks || false;
        
        // Get location options for the selector
        let locationOptionsHtml = '';
        const existingLocations = options.locationOptions || [];
        
        if (existingLocations.length > 0) {
            locationOptionsHtml = existingLocations
                .map(loc => `<option value="${loc}" ${loc === data.location ? 'selected' : ''}>${loc}</option>`)
                .join('');
        } else {
            locationOptionsHtml = `<option value="${data.location || ''}" selected>${data.location || ''}</option>`;
        }
        
        // Generate HTML for the row template
        // CRITICAL: Ensure all modal IDs are in standardized format "containersModal{recordId}"
        // with matching aria-labelledby="containersModalLabel{recordId}"
        const rowHtml = `
            <tr class="countRow ${data.counted ? 'approved' : ''}" data-countrecord-id="${recordId}">
                <td data-countrecord-id="${recordId}" class="tbl-cell-item_code text-right">
                    <div class="dropdown">
                        <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown" ${disableLabelLinks ? 'readonly="readonly"' : ''}>${data.item_code}</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item partialContainerLabelLink" data-itemcode="${data.item_code}">Partial Container Label</a></li>
                        </ul>
                    </div>
                    </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-item_description">${data.item_description || ''}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-expected_quantity">
                    <span data-countrecord-id="${recordId}" class="expected-quantity-span">${parseFloat(data.expected_quantity || 0).toFixed(4)}</span> <em>${data.standard_uom || ''}</em>
                    <span></span> <i class="fa fa-refresh qtyrefreshbutton" itemcode="${data.item_code}" data-countrecord-id="${recordId}" aria-hidden="true"></i>
                    </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-containers">
                    <button class="containers" data-countrecord-id="${recordId}" data-bs-toggle="modal" data-bs-target="#containersModal${recordId}">Enter ></button>
                    <div class="modal fade" id="containersModal${recordId}" tabindex="-1" aria-labelledby="containersModalLabel${recordId}" aria-hidden="true">
                        <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button class="btn btn-secondary multi-container-print-button" data-countrecord-id="${recordId}" title="Print All Container Labels">
                                    <i class="fa fa-print" aria-hidden="true"></i> Print All
                                </button>
                                <h5 class="modal-title" id="containersModalLabel${recordId}">Containers for ${data.item_code}: <p class="containerQuantity"></p></h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <table class="container-table" data-countrecord-id="${recordId}">
                                    <thead class="containerHeader">
                                        <tr>
                                            <th style="display:none;">container_id</th>
                                            <th>Quantity</th>
                                            <th>Container Type</th>
                                            <th class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">Tare Weight</th>
                                            <th class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">NET</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody class="containerTbody"></tbody>
                                </table>
                                <div style="padding-top: 10px;"><button type="button" data-countrecord-id="${recordId}" class="btn btn-lg btn-primary add-container-row"> + </button></div>
                                <div class="container-monitor" data-countrecord-id="${recordId}" style="display:none;" data-container-id-updated=""></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-success" data-bs-dismiss="modal">Save</button>
                            </div>
                        </div>
                        </div>
                    </div>
                    </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted_quantity">
                    <input class="counted_quantity" readonly data-bs-toggle="modal" data-bs-target="#containersModal${recordId}" type="number" data-countrecord-id="${recordId}" value="${parseFloat(data.counted_quantity || 0).toFixed(0)}" step="0.00001">
                    </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted_date noPrint" readonly>${data.counted_date || ''}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-variance text-right noPrint">${parseFloat(data.variance || 0).toFixed(0)}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted text-center noPrint ${data.counted ? 'checkedcountedcell' : 'uncheckedcountedcell'}">
                    <input data-countrecord-id="${recordId}" class="counted-input" type="checkbox" ${data.counted ? 'checked' : ''}>
                        </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-count_type text-right noPrint" style="display:none;">${data.count_type || ''}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-collection_id text-right" style="display:none;">${data.collection_id || ''}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-comment">
                    <textarea class="comment" data-countrecord-id="${recordId}" cols="10" rows="1">${data.comment || 'None'}</textarea>
                        </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-zone">
                    <select data-countrecord-id="${recordId}" class="location-selector">
                        ${locationOptionsHtml}
                            </select>
                        </td>
                <td class="discardButtonCell text-center noPrint">
                    <i class="fa-solid fa-trash-alt discardButton" data-countrecord-id="${recordId}" data-countlist-id="${options.listId || document.querySelector('#countsTable')?.getAttribute('data-countlist-id') || ''}" aria-hidden="true"></i>
                        </td>
                    </tr>
                `;
        
        // Create a DOM element from the HTML
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = rowHtml.trim();
        
        // Validate the created DOM structure
        if (!tempContainer.querySelector('tr') || !tempContainer.querySelector('.modal')) {
            console.error(`❌ Failed to create valid row from HTML template for ${recordId}`);
            return null;
        }
        
        // Extract just the row element
        const rowElement = tempContainer.querySelector('tr');
        
        // Log the creation and perform final checks
        console.log(`✅ Row template created for record ID ${recordId}`);
        
        // Return the new row element
        return rowElement;
    }
    
    /**
     * Verifies and fixes modal bindings within a row to ensure they use the correct record ID
     * @private
     */
    _verifyModalBindings(row, recordId) {
        try {
            console.log(`🔍 Verifying modal bindings for row ${recordId}`);
            
            // 1. Find all modal-related elements in the row
            const containerButton = row.querySelector('button.containers');
            if (!containerButton) {
                console.warn(`❓ No container button found in row ${recordId}`);
                return false;
            }
            
            const countedQuantityInput = row.querySelector('input.counted_quantity');
            const containerCell = row.querySelector('.tbl-cell-containers');
            if (!containerCell) {
                console.warn(`❓ No container cell found in row ${recordId}`);
                return false;
            }
            
            const modal = containerCell.querySelector('.modal');
            if (!modal) {
                console.warn(`❓ No modal found in row ${recordId}`);
                return false;
            }
            
            // 2. Get the current modal ID and verify it's the standard format
            const currentModalId = modal.id;
            const standardModalId = `containersModal${recordId}`;
            
            if (currentModalId !== standardModalId) {
                console.warn(`⚠️ Modal ID needs standardization: ${currentModalId} → ${standardModalId}`);
                
                // Set the standard ID format
                modal.id = standardModalId;
                console.log(`✏️ Updated modal ID to standard format: ${standardModalId}`);
                
                // Update button target
                containerButton.setAttribute('data-bs-target', `#${standardModalId}`);
                console.log(`✏️ Updated container button target to #${standardModalId}`);
                
                // Update input target
                if (countedQuantityInput) {
                    countedQuantityInput.setAttribute('data-bs-target', `#${standardModalId}`);
                    console.log(`✏️ Updated counted quantity input target to #${standardModalId}`);
                }
                
                // Update modal title ID
                const modalTitle = modal.querySelector('.modal-title');
                if (modalTitle) {
                    modalTitle.id = `containersModalLabel${recordId}`;
                    console.log(`✏️ Updated modal title ID to containersModalLabel${recordId}`);
                }
                
                // Update aria-labelledby attribute on the modal
                modal.setAttribute('aria-labelledby', `containersModalLabel${recordId}`);
            }
            
            // 3. Double-check the button targets the correct modal
            const buttonTarget = containerButton.getAttribute('data-bs-target');
            if (buttonTarget !== `#${standardModalId}`) {
                console.warn(`⚠️ Container button target needs correction: ${buttonTarget} → #${standardModalId}`);
                containerButton.setAttribute('data-bs-target', `#${standardModalId}`);
            }
            
            // 4. Ensure counted quantity input also targets the correct modal
            if (countedQuantityInput) {
                const inputTarget = countedQuantityInput.getAttribute('data-bs-target');
                if (inputTarget !== `#${standardModalId}`) {
                    console.warn(`⚠️ Counted quantity input target needs correction: ${inputTarget} → #${standardModalId}`);
                    countedQuantityInput.setAttribute('data-bs-target', `#${standardModalId}`);
                }
            }
            
            // 5. Check for and clear existing click handlers to prevent duplicates
            if (jQuery) {
                try {
                    $(containerButton).off('click'); // Clear any previous handlers
                    if (countedQuantityInput) {
                        $(countedQuantityInput).off('click');
                    }
                    console.log(`🧹 Cleared existing click handlers to prevent conflicts`);
                } catch (e) {
                    console.warn(`Failed to clear jQuery click handlers:`, e);
                }
            }
            
            // 6. Delegate to the WebSocket's more thorough binding method if available
            if (typeof CountListWebSocket !== 'undefined' && this.countListWebSocket instanceof CountListWebSocket) {
                console.log(`📡 Delegating to WebSocket's modal binding ritual...`);
                this.countListWebSocket._ensureProperModalBindings(row, recordId);
            } else {
                console.log(`🔄 Using local modal binding verification only - WebSocket not available`);
                
                // Re-initialize modal manually
                if (window.bootstrap && window.bootstrap.Modal) {
                    const modalInstance = new window.bootstrap.Modal(modal);
                    console.log(`✨ Manually re-initialized Bootstrap modal without WebSocket`);
                    
                    // Add direct click handlers as fallback
                    containerButton.onclick = (e) => {
                        console.log(`🖱️ Container button clicked, manually showing modal`);
                        modalInstance.show();
                    };
                    
                    if (countedQuantityInput) {
                        countedQuantityInput.onclick = (e) => {
                            console.log(`🖱️ Counted quantity input clicked, manually showing modal`);
                            modalInstance.show();
                        };
                    }
                }
            }
            
            console.log(`✅ Modal binding verification completed for row ${recordId}`);
            return true;
        } catch (error) {
            console.error(`💥 Error verifying modal bindings for row ${recordId}:`, error);
            return false;
        }
    }

    initializeMobileCardToggles() {
        // Add toggle buttons to existing rows
        document.querySelectorAll('.countRow').forEach(row => {
            this.addMobileToggle(row);
        });
    
        // Set default state to collapsed
        document.querySelectorAll('.countRow').forEach(row => {
            row.classList.add('collapsed');
        });
    
        // Add approved class based on checkbox state
        this.updateApprovedStates();
    }
    
    addMobileToggle(row) {
        if (!row.querySelector('.mobile-toggle')) {
            const itemCodeLink = row.querySelector('.itemCodeDropdownLink');
            const itemCode = itemCodeLink ? itemCodeLink.textContent.trim() : 'Item';
            const itemDescription = row.querySelector('[data-label="Description"]')?.textContent.trim() || '';
            
            const toggleHTML = `
                <td class="mobile-header-cell">
                    <div class="mobile-card-header">
                        <div class="mobile-header-content">
                            <span class="item-code">${itemCode}</span>
                            <span class="item-description">${itemDescription}</span>
                        </div>
                        <span class="toggle-icon">▼</span>
                    </div>
                </td>
            `;
            
            // Insert as first cell
            row.insertAdjacentHTML('afterbegin', toggleHTML);
            
            // Add click handler
            const header = row.querySelector('.mobile-card-header');
            header.addEventListener('click', () => {
                row.classList.toggle('expanded');
                row.classList.toggle('collapsed');
            });
        }
    }

    updateApprovedStates() {
        document.querySelectorAll('.countRow').forEach(row => {
            const checkbox = row.querySelector('.counted-input');
            if (checkbox?.checked) {
                row.classList.add('approved');
            } else {
                row.classList.remove('approved');
            }
        });
    }

    /**
     * Adds a new count record row to the UI and sets up all event handlers
     * @param {string|number} recordId - The ID of the count record
     * @param {Object} data - The data for the new row
     * @param {Object} options - Additional options
     */
    addCountRecordRow(recordId, data, options = {}) {
        console.log(`🧪 Adding new count record row ${recordId} with data:`, data);
        
        try {
            // Get the table and verify it exists
            const table = document.getElementById('countsTable');
            if (!table) {
                console.error("❌ Error: Cannot find countsTable element!");
                return null;
            }
            
            // Get table body and verify it exists
            const tbody = table.querySelector('tbody');
            if (!tbody) {
                console.error("❌ Error: Cannot find tbody in countsTable!");
                return null;
            }
            
            // Create the row using our template function
            const row = this.createCountRecordRow(recordId, data, options);
            
            // Find the Add Item row if it exists
            const addItemRow = Array.from(tbody.querySelectorAll('tr')).find(row => 
                row.querySelector('button[data-bs-target="#addCountListItemModal"]') || 
                row.querySelector('#modalToggle')
            );
            
            // Insert the row in the appropriate position
            if (addItemRow) {
                console.log(`📌 Inserting new row before Add Item row`);
                tbody.insertBefore(row, addItemRow);
            } else {
                console.log(`📌 Appending new row to end of table`);
                tbody.appendChild(row);
            }
            
            // CRITICAL: Verify modal bindings AFTER insertion to DOM
            console.log(`⚠️ Critical: Double-checking modal bindings after insertion`);
            this._verifyModalBindings(row, recordId);
            
            // Force Bootstrap to initialize all components in the row
            this._initializeBootstrapComponents(row);
            
            // Setup event handlers
            this._setupSingleRowEventHandlers(row, this.countListWebSocket);
            
            // Initialize the container table for this row if applicable
            if (typeof ContainerManager !== 'undefined' && this.countListWebSocket) {
                try {
                    console.log(`🪄 Initializing container manager for row ${recordId}`);
                    ContainerManager.renderContainerRows(recordId);
                } catch (err) {
                    console.warn(`⚠️ Failed to initialize container manager for row ${recordId}:`, err);
                }
            }
            
            // Add container monitor to mutation observer if present
            const containerMonitor = row.querySelector('.container-monitor');
            if (containerMonitor && this.mutationObserver) {
                this._addContainerMonitorToObserver(containerMonitor, this.countListWebSocket);
            }
            
            // Highlight the row briefly to draw attention
            $(row).css({
                'backgroundColor': '#ffddad',
                'transition': 'background-color 2s ease-in-out'
            });
            
            // Force a DOM reflow to ensure the row is visible
            void row.offsetHeight;
            
            // Scroll to make the row visible
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });

            this.addMobileToggle(row);
            row.classList.add('collapsed');
            
            if (data.counted) {
                row.classList.add('approved');
            }
            
            setTimeout(() => {
                $(row).css('backgroundColor', '');
                
                // SUPER CRITICAL: Perform final triple-check of modal bindings
                // This ensures the modal is correctly initialized AFTER all DOM changes
                console.log(`🔮 Performing final modal binding checks for row ${recordId}`);
                if (typeof CountListWebSocket !== 'undefined' && this.countListWebSocket instanceof CountListWebSocket) {
                    this.countListWebSocket._ensureProperModalBindings(row, recordId);
                }
            }, 500);
            
            return row;
        } catch (error) {
            console.error(`💥 Failed to add count record row ${recordId}:`, error);
            return null;
        }
    }
    
    _initializeBootstrapComponents(row) {
        try {
            console.log(`🔄 Initializing Bootstrap components for row`);
            
            // Initialize dropdowns
            row.querySelectorAll('[data-bs-toggle="dropdown"]').forEach(element => {
                if (window.bootstrap && window.bootstrap.Dropdown) {
                    new window.bootstrap.Dropdown(element);
                }
            });
            
            // Initialize tooltips
            row.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(element => {
                if (window.bootstrap && window.bootstrap.Tooltip) {
                    new window.bootstrap.Tooltip(element);
                }
            });
            
            // Initialize modals
            row.querySelectorAll('.modal').forEach(element => {
                if (window.bootstrap && window.bootstrap.Modal) {
                    new window.bootstrap.Modal(element);
                }
            });
            
            console.log(`✅ Bootstrap components initialized`);
        } catch (error) {
            console.warn(`⚠️ Error initializing Bootstrap components:`, error);
        }
    }
    
    /**
     * Sets up event handlers for a single count record row
     * @private
     */
    _setupSingleRowEventHandlers(rowElement, thisCountListWebSocket) {
        // Counted quantity change handler
        $(rowElement).find('input.counted_quantity').off('change').on('change', function(e) {
            calculateVarianceAndCount($(this).closest('tr').attr('data-countrecord-id'));
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });
        
        // Location selector change handler
        $(rowElement).find('select.location-selector').off('change').on('change', function() {
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });
        
        // Comment field input handler
        $(rowElement).find('textarea.comment').off('input').on('input', function() {
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });
        
        // checkbox handler
        $(rowElement).find('input.counted-input').off('change.global').on('change.global', function(){
            const row = $(this).closest('tr.countRow');

            if (row.length) { // Ensure the row was found
                if (this.checked) {
                    row.addClass('approved');
                    row.css('box-shadow', '0 0 15px rgba(145, 255, 165, 0.6)');
                    setTimeout(() => row.css('box-shadow', ''), 1000);
                } else {
                    row.removeClass('approved');
                    row.css('box-shadow', '');
                }
            } else {
                console.warn('[VLAUDE_DEBUG_GLOBAL] Could not find parent tr.countRow for checkbox:', this);
            }

            // Defer other operations
            setTimeout(() => {
                updateCheckBoxCellColors();
                sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
            }, 0);
        });
        
        // Textarea expand/contract handlers
        const commentField = $(rowElement).find('textarea.comment')[0];
        if (commentField) {
            commentField.addEventListener("focus", function() {
                commentField.setAttribute("rows", "10");
                commentField.setAttribute("cols", "40");
            });
            commentField.addEventListener("blur", function() {
                commentField.setAttribute("rows", "1");
                commentField.setAttribute("cols", "10");
            });
        }
        
        // Discard button handler
        $(rowElement).find('.discardButton').off('click').on('click', function() {
            if (confirm("Are you sure you want to delete this record?")) {
                const recordId = $(this).attr("data-countrecord-id");
                const listId = $(this).attr("data-countlist-id");
                const recordType = getURLParameter("recordType");
                thisCountListWebSocket.deleteCount(recordId, recordType, listId);
            }
        });
        
        // Quantity refresh button handler
        $(rowElement).find('.qtyrefreshbutton').off('click').on('click', function() {
            console.log("qtyrefreshbutton click event fired", this);
            let shouldProceed = window.confirm("Are you sure you want to update this quantity?\nThis action CANNOT be undone.");
            if (shouldProceed) {
                const recordId = $(this).attr("data-countrecord-id");
                const recordType = getURLParameter("recordType");
                thisCountListWebSocket.refreshOnHand(recordId, recordType);
            }
        });
        
        // Date cell click handler
        $(rowElement).off('click').on('click', function() {
            const countedDateCell = $(this).find('td.tbl-cell-counted_date');
            const today = new Date();
            const formattedDate = today.toISOString().split('T')[0];
            if (countedDateCell.length > 0) {
                countedDateCell.text(formattedDate);
            }
        });
        
        // Container label link handler
        $(rowElement).find(".partialContainerLabelLink").off('click').on('click', function() {
            document.getElementById("blendLabelDialog").showModal();
            let thisItemCode = $(this).attr('data-itemcode');
            let encodedItemcode = btoa(thisItemCode);
            let itemInformation;
            $.ajax({
                url: '/core/item-info-request?lookup-type=itemCode&item=' + encodedItemcode,
                async: false,
                dataType: 'json',
                success: function(data) {
                    itemInformation = data;
                }
            });
            let thisItemDescription = itemInformation.item_description;
            $("#inventory-label-item-code").text(thisItemCode);
            $("#inventory-label-item-description").text(thisItemDescription);
        });
    }
    
    /**
     * Adds a container monitor element to the mutation observer
     * @private
     */
    _addContainerMonitorToObserver(containerMonitor, thisCountListWebSocket) {
        try {
            const self = this;
            const observer = new MutationObserver((mutationsList) => {
                for (let mutation of mutationsList) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'data-container-id-updated') {
                        const countRecordId = mutation.target.getAttribute('data-countrecord-id');
                        const updatedContainerId = mutation.target.getAttribute('data-container-id-updated');
                        const recordType = getURLParameter('recordType');
                        console.log(`Container monitor updated for countRecordId: ${countRecordId}, new containerId: ${updatedContainerId}`);
                        self.updateContainerFields(countRecordId, recordType, updatedContainerId, thisCountListWebSocket);
                    }
                }
            });
            
            observer.observe(containerMonitor, { attributes: true });
            console.log(`🔍 Container monitor observer added for record ${containerMonitor.getAttribute('data-countrecord-id')}`);
        } catch (e) {
            console.error("Failed to set up container monitor observer:", e);
        }
    }

    setupLabelLinks() {
        const links = $(".partialContainerLabelLink");
        links.each(function() {
            $(this).click(function() {
                document.getElementById("blendLabelDialog").showModal();
                let thisItemCode = $(this).attr('data-itemcode');
                let encodedItemcode = btoa(thisItemCode);
                let itemInformation;
                $.ajax({
                    url: '/core/item-info-request?lookup-type=itemCode&item=' + encodedItemcode,
                    async: false,
                    dataType: 'json',
                    success: function(data) {
                        itemInformation = data;
                    }
                });
                let thisItemDescription = itemInformation.item_description;
                $("#inventory-label-item-code").text(thisItemCode);
                $("#inventory-label-item-description").text(thisItemDescription);
            });
        });
    }

    /**
     * Initialize container fields is now delegated to the ContainerManager
     * This method is kept for backward compatibility but just calls the manager
     */
    initializeContainerFields() {
        // Forward the latest WebSocket reference to ContainerManager
        this.containerManager.initializeAllContainerFields(this.webSocket);
    };

    /**
     * Update container fields is now delegated to the ContainerManager
     * This method is kept for backward compatibility but just calls the manager
     */
    updateContainerFields(countRecordId, recordType, containerId, thisCountListWebSocket) {
        console.log(`Forwarding container update to ContainerManager for record ${countRecordId}, container ${containerId}`);
        
        // Make sure the ContainerManager has the latest websocket reference
        this.containerManager.webSocket = thisCountListWebSocket;
        
        // Call the manager's method to update the containers
        this.containerManager.updateContainerTable(countRecordId, recordType, containerId);
    };

    setUpEventListeners(thisCountListWebSocket) {
        $('input.counted_quantity').change(function(e){
            calculateVarianceAndCount($(this).closest('tr').attr('data-countrecord-id'));
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });
        $('select.location-selector').change(function(){
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });
        $('textarea.comment').on('input', function(){
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
        });

        // Modified checkbox handler in setUpEventListeners
        $('input.counted-input').off('change.global').on('change.global', function(){
            const row = $(this).closest('tr.countRow');

            if (row.length) { // Ensure the row was found
                if (this.checked) {
                    row.addClass('approved');
                    row.css('box-shadow', '0 0 15px rgba(145, 255, 165, 0.6)');
                    setTimeout(() => row.css('box-shadow', ''), 1000);
                } else {
                    row.removeClass('approved');
                    row.css('box-shadow', '');
                }
            } else {
                console.error('Could not find parent tr.countRow for checkbox:', this);
            }

            // Defer other operations
            setTimeout(() => {
                updateCheckBoxCellColors();
                sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
            }, 0);
        });

        $('tr').click(function() {
            const countedDateCell = $(this).find('td.tbl-cell-counted_date');
            const today = new Date();
            const formattedDate = today.toISOString().split('T')[0];
            if (countedDateCell.length > 0) {
                countedDateCell.text(formattedDate);
            }
        });

        const commentFields = document.querySelectorAll('textarea');
        commentFields.forEach((field) => {
            field.addEventListener("focus", function(){
                field.setAttribute("rows", "10");
                field.setAttribute("cols", "40");
            });
            field.addEventListener("blur", function(){
                field.setAttribute("rows", "1");
                field.setAttribute("cols", "10");
            });
        });

        $('.qtyrefreshbutton').each(function(){
            $(this).click(function(){
                console.log("qtyrefreshbutton click event fired", this);
                let shouldProceed = window.confirm("Are you sure you want to update this quantity?\nThis action CANNOT be undone.");
                if (shouldProceed) {
                    const recordId = $(this).attr("data-countrecord-id");
                    const recordType = getURLParameter("recordType");
                    thisCountListWebSocket.refreshOnHand(recordId, recordType);
                }
            });
        });

        $('.discardButton').each(function(){
            $(this).click(function(){
                // console.log("discardButton click event fired", this);
                if (confirm("Are you sure you want to delete this record?")) {
                    const recordId = $(this).attr("data-countrecord-id");
                    const listId = $(this).attr("data-countlist-id");
                    const recordType = getURLParameter("recordType");
                    thisCountListWebSocket.deleteCount(recordId, recordType, listId);
                } else {
                    return;
                } 
            });
        });

        // Prefetch UoM data when a container modal is shown
        $('body').on('show.bs.modal', '.modal', function (event) {
            const modalId = $(this).attr('id');
            if (modalId && modalId.startsWith('containersModal')) {
                const countRecordId = modalId.replace('containersModal', '');
                if (countRecordId) {
                    console.log(`[UOM-PREFETCH] Modal for ${countRecordId} is showing. Initiating UoM prefetch.`);
                    const recordType = getURLParameter('recordType') || 'blendcomponent'; // Default to blendcomponent if not in URL
                    // Call _convertQuantityIfNeeded with a dummy quantity (0) to trigger cache population
                    _convertQuantityIfNeeded(countRecordId, 0, recordType); 
                }
            }
        });
    };

    setUpMutationObservers(thisCountListWebSocket) {
        // Store reference to this to use in the observer callback
        const self = this;

        const containerMonitorObserver = new MutationObserver((mutationsList) => {
            for (let mutation of mutationsList) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-container-id-updated') {
                    const countRecordId = mutation.target.getAttribute('data-countrecord-id');
                    const updatedContainerId = mutation.target.getAttribute('data-container-id-updated');
                    const recordType = getURLParameter('recordType');
                    console.log(`Container monitor updated for countRecordId: ${countRecordId}, new containerId: ${updatedContainerId}`);
                    self.updateContainerFields(countRecordId, recordType, updatedContainerId, thisCountListWebSocket);
                }
            }
        });

        // Observe changes to all div.container-monitor elements
        document.querySelectorAll('div.container-monitor').forEach((element) => {
            containerMonitorObserver.observe(element, { attributes: true });
        });
    };

};

export class MaxProducibleQuantityPage {
    constructor() {
        try {
            const urlParameters = new URLSearchParams(window.location.search);
            const itemCode = atob(urlParameters.get('itemCode'));
            const itemData = getMaxProducibleQuantity(itemCode, "NoComponentItemFilter", "itemCode");
            this.setMaxProducibleQuantityDiv(itemData)
        } catch(err) {
            console.error(err.message);
        }
    };

    setMaxProducibleQuantityDiv(itemData){
        $("#itemCodeAndDescription").text(`${itemData.item_code} ${itemData.item_description}:`);
        $("#max_producible_quantity").text(`${itemData.max_producible_quantity} gallons`);
        $("#max_producible_quantity").css('font-weight', 'bold');
        $("#limiting_factor").text(`${itemData.limiting_factor_item_code}: ${itemData.limiting_factor_item_description}`);
        $("#limiting_factor_onhand").text(
            `${Math.round(itemData.limiting_factor_quantity_onhand, 0)}
            ${itemData.limiting_factor_UOM} on hand now.
            ${Math.round(itemData.limiting_factor_OH_minus_other_orders)}  ${itemData.limiting_factor_UOM} available after all other usage is taken into account.`
            );
        if (itemData.limiting_factor_OH_minus_other_orders < 0) {
            $("#limiting_factor_onhand").css('color', 'red').css('font-weight', 'bold');
        }
        $("#next_shipment").text(`${itemData.next_shipment_date}`);
        if (Object.keys(itemData.consumption_detail[itemData.limiting_factor_item_code]).length > 1){
            $("#limiting_factor_usage_table_container").show()
            for (const key in itemData.consumption_detail[itemData.limiting_factor_item_code]) {
                let thisRow = document.getElementById("limiting_factor_usage_tbody").insertRow();
                let blendItemCodeCell = thisRow.insertCell(0);
                let blendDescriptionCell = thisRow.insertCell(1);
                blendDescriptionCell.innerHTML = itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_item_description'];
                let blendQuantityCell = thisRow.insertCell(2);
                blendQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_total_qty_needed'])).toString() + ' gallons';
                let blendShortTimeCell = thisRow.insertCell(3);
                blendShortTimeCell.innerHTML = parseFloat(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_first_shortage']).toFixed(2).toString() + ' hours';
                let componentQuantityCell = thisRow.insertCell(4);
                componentQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['component_usage'])).toString() + ' ' + itemData.limiting_factor_UOM;
                componentQuantityCell.style['text-align'] = 'right';
                if (key == 'total_component_usage'){
                    blendItemCodeCell.innerHTML = "TOTAL USAGE FOR OTHER ORDERS"
                    thisRow.style.backgroundColor = 'lightgray';
                    thisRow.style.fontWeight = 'bold';
                    blendDescriptionCell.innerHTML = '';
                    blendQuantityCell.innerHTML = '';
                    blendShortTimeCell.innerHTML = '';
                    componentQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code]['total_component_usage']).toString() + ' ' + itemData.limiting_factor_UOM);
                } else {
                    blendItemCodeCell.innerHTML = key;
                }
            }
        };
        $("#component_quantity_header").text(`${itemData.limiting_factor_item_code} Qty Used`)
        $("#next_shipment_header").text(`Next Shipment of ${itemData.limiting_factor_item_code}:`)
        $("#blendCapacityContainer").show();
    }

};

export class BaseTemplatePage {
    constructor() {
        try {
            this.miscReportCommands = [];
            this.externalCommandPaletteEntries = [];
            this._authState = this.determineAuthenticationState();
            this.changeNavColor();
            this.checkRefreshStatus();
            this.setUpConnectionStatusCheck();
            this.setupCommandPalette();
            this.registerCommandPaletteEntries(this.buildProductionScheduleCommandEntries());
            this.prefetchMiscReportCommands();
        } catch(err) {
            console.error(err.message);
        };
    };

    checkRefreshStatus(){
        let rStat;
        $.ajax({
            url: '/core/get-refresh-status/',
            async: false,
            dataType: 'json',
            success: function(data) {
                rStat = data;
            }
        });
        if (rStat.status == "down") {
            $("#refreshWarningLink").show();
        };
    };

    changeNavColor() {
        if (location.href.includes('rpm') || location.href.includes('jrd')){
            $("#theNavBar").removeClass('bg-primary');
            $("#theNavBar").prop('style', 'background-color:#ffa500;');
            $("#theNavBar a.nav-link").css('color', '#007bff');
        };
    };

    determineAuthenticationState() {
        if (typeof this._authState === 'boolean') {
            return this._authState;
        }
        const body = document.body;
        if (body) {
            const datasetValue = body.dataset ? body.dataset.userAuthenticated : null;
            if (datasetValue === 'true') {
                this._authState = true;
                return this._authState;
            }
            if (datasetValue === 'false') {
                this._authState = false;
                return this._authState;
            }
            const attrValue = body.getAttribute && body.getAttribute('data-user-authenticated');
            if (attrValue === 'true' || attrValue === 'false') {
                this._authState = attrValue === 'true';
                return this._authState;
            }
        }
        const authLink = document.querySelector('.quick-find-wrapper .auth-item a');
        if (authLink) {
            const label = (authLink.textContent || authLink.getAttribute('aria-label') || '').toLowerCase();
            if (label.includes('log out') || label.includes('logout')) {
                this._authState = true;
                return this._authState;
            }
            if (label.includes('log in') || label.includes('login')) {
                this._authState = false;
                return this._authState;
            }
        }
        this._authState = null;
        return this._authState;
    };

    setUpConnectionStatusCheck(){
        window.addEventListener('load', function() {
        var offlineBanner = document.getElementById('networkStatusBar');
        var myForm = document.querySelector('form');
        if (myForm){
            function updateOnlineStatus() {
                if(navigator.onLine) {
                  offlineBanner.style.display = 'none';
                  myForm.querySelector('button[type="submit"]').disabled = false;
                } else {
                  offlineBanner.style.display = 'block';
                  myForm.querySelector('button[type="submit"]').disabled = true;
                }
              }
              
              window.addEventListener('online', updateOnlineStatus);
              window.addEventListener('offline', updateOnlineStatus);
              
              updateOnlineStatus();
        };
        
      });
    };
      
    setupCommandPalette() {
        const modalElement = document.getElementById('commandPaletteModal');
        if (!modalElement || typeof bootstrap === 'undefined' || !bootstrap.Modal) {
            return;
        }

        const toggleButton = document.getElementById('commandPaletteToggle');
        const inputElement = document.getElementById('commandPaletteInput');
        const resultsContainer = document.getElementById('commandPaletteResults');
        const emptyStateElement = document.getElementById('commandPaletteEmptyState');

        if (!inputElement || !resultsContainer || !emptyStateElement) {
            return;
        }

        const self = this;
        const existingInstance = bootstrap.Modal.getInstance(modalElement);
        if (existingInstance) {
            existingInstance.dispose();
        }
        const modalInstance = new bootstrap.Modal(modalElement, { keyboard: true });

        let commandsCache = null;
        let filteredCommands = [];
        let activeIndex = -1;
        let searchSequence = 0;
        self._invalidateCommandCache = function() {
            commandsCache = null;
        };

        const ensureCommands = function(force) {
            if (!force && commandsCache) {
                return commandsCache;
            }
            commandsCache = self.buildCommandPaletteEntries();
            return commandsCache;
        };

        const schedulePreload = function() {
            const build = function() {
                if (!commandsCache) {
                    commandsCache = self.buildCommandPaletteEntries();
                }
            };
            if (typeof window.requestIdleCallback === 'function') {
                window.requestIdleCallback(build, { timeout: 1000 });
            } else {
                window.setTimeout(build, 500);
            }
        };

        const resetResults = function() {
            resultsContainer.innerHTML = '';
            filteredCommands = [];
            activeIndex = -1;
        };

        const showEmptyState = function(message) {
            emptyStateElement.textContent = message;
            emptyStateElement.classList.remove('d-none');
        };

        const hideEmptyState = function() {
            emptyStateElement.classList.add('d-none');
        };

        const setActiveResult = function(index, shouldFocus) {
            const items = resultsContainer.querySelectorAll('[data-command-index]');
            if (!items.length) {
                activeIndex = -1;
                return;
            }

            let targetIndex = index;
            if (targetIndex < 0) {
                targetIndex = 0;
            }
            if (targetIndex >= items.length) {
                targetIndex = items.length - 1;
            }

            for (let i = 0; i < items.length; i += 1) {
                const item = items[i];
                const isActive = i === targetIndex;
                item.classList.toggle('active', isActive);
                item.setAttribute('aria-selected', isActive ? 'true' : 'false');
                item.setAttribute('tabindex', isActive ? '0' : '-1');
            }

            activeIndex = targetIndex;

            const targetItem = items[targetIndex];
            if (shouldFocus !== false && targetItem) {
                targetItem.focus();
            }

            const containerRect = resultsContainer.getBoundingClientRect();
            const itemRect = targetItem.getBoundingClientRect();
            if (itemRect.top < containerRect.top) {
                resultsContainer.scrollTop -= (containerRect.top - itemRect.top);
            } else if (itemRect.bottom > containerRect.bottom) {
                resultsContainer.scrollTop += (itemRect.bottom - containerRect.bottom);
            }
        };

        const renderResults = function(items, query) {
            resultsContainer.innerHTML = '';
            if (!items.length) {
                showEmptyState(query ? 'No matching destinations.' : 'Start typing to search.');
                activeIndex = -1;
                return;
            }

            hideEmptyState();

            const fragment = document.createDocumentFragment();
            for (let i = 0; i < items.length; i += 1) {
                const command = items[i];
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'list-group-item list-group-item-action command-palette__item';
                button.dataset.commandIndex = i.toString();
                button.dataset.commandHref = command.href;
                button.setAttribute('role', 'option');
                button.setAttribute('tabindex', '-1');

                const labelSpan = document.createElement('span');
                labelSpan.className = 'command-palette__label';
                labelSpan.textContent = command.label;
                button.appendChild(labelSpan);

                if (command.groupLabel) {
                    const groupSpan = document.createElement('span');
                    groupSpan.className = 'command-palette__group';
                    groupSpan.textContent = command.groupLabel;
                    button.appendChild(groupSpan);
                }

                fragment.appendChild(button);
            }

            resultsContainer.appendChild(fragment);
            setActiveResult(0, false);
        };

        const filterCommands = function(allCommands, query) {
            if (!query) {
                return [];
            }
            const normalizedQuery = query.toLowerCase();

            const evaluateMatch = function(value, type) {
                if (typeof value !== 'string' || !value) {
                    return null;
                }
                const index = value.indexOf(normalizedQuery);
                if (index === -1) {
                    return null;
                }
                const exact = value === normalizedQuery;
                return { value: value, type: type, index: index, exact: exact };
            };

            const selectBestKeywordMatch = function(keywordsLower) {
                if (!Array.isArray(keywordsLower) || !keywordsLower.length) {
                    return null;
                }
                let best = null;
                for (let i = 0; i < keywordsLower.length; i += 1) {
                    const keyword = keywordsLower[i];
                    if (typeof keyword !== 'string') {
                        continue;
                    }
                    const result = evaluateMatch(keyword, 'keyword');
                    if (!result) {
                        continue;
                    }
                    if (!best) {
                        best = result;
                        continue;
                    }
                    if (result.exact && !best.exact) {
                        best = result;
                        continue;
                    }
                    if (result.index === 0 && best.index !== 0) {
                        best = result;
                        continue;
                    }
                    if (result.index < best.index) {
                        best = result;
                        continue;
                    }
                }
                return best;
            };

            const matchPriority = function(match) {
                const type = match.type;
                const isExact = match.exact;
                const isPrefix = match.index === 0;
                if (type === 'label') {
                    if (isExact) { return 0; }
                    if (isPrefix) { return 1; }
                    return 2;
                }
                if (type === 'keyword') {
                    if (isExact) { return 3; }
                    if (isPrefix) { return 4; }
                    return 5;
                }
                if (type === 'group') {
                    if (isExact) { return 6; }
                    if (isPrefix) { return 7; }
                    return 8;
                }
                return 9;
            };

            const computeMatchMetadata = function(command) {
                const labelLower = command.labelLower || '';
                const groupLower = command.groupLower || '';
                const keywordsLower = Array.isArray(command.keywordsLower) ? command.keywordsLower : [];

                const labelMatch = evaluateMatch(labelLower, 'label');
                const keywordMatch = selectBestKeywordMatch(keywordsLower);
                const groupMatch = evaluateMatch(groupLower, 'group');

                const potentialMatches = [];
                if (labelMatch) {
                    potentialMatches.push(labelMatch);
                }
                if (keywordMatch) {
                    potentialMatches.push(keywordMatch);
                }
                if (groupMatch) {
                    potentialMatches.push(groupMatch);
                }

                if (!potentialMatches.length) {
                    return null;
                }

                potentialMatches.sort(function(a, b) {
                    const priorityDiff = matchPriority(a) - matchPriority(b);
                    if (priorityDiff !== 0) {
                        return priorityDiff;
                    }
                    if (a.index !== b.index) {
                        return a.index - b.index;
                    }
                    return (a.value.length || 0) - (b.value.length || 0);
                });

                const match = potentialMatches[0];
                const priority = matchPriority(match);
                const remainderLength = Math.max(
                    0,
                    match.value.length - (match.index + normalizedQuery.length)
                );

                let score = (priority * 1000) + (match.index * 10) + remainderLength;
                if (match.value.indexOf('schedule') > -1) {
                    score -= 50;
                }

                return {
                    command: command,
                    score: score,
                    priority: priority,
                    remainderLength: remainderLength
                };
            };

            const scoredMatches = [];
            for (let i = 0; i < allCommands.length; i += 1) {
                const command = allCommands[i];
                const metadata = computeMatchMetadata(command);
                if (metadata) {
                    scoredMatches.push(metadata);
                }
            }

            scoredMatches.sort(function(a, b) {
                if (a.score !== b.score) {
                    return a.score - b.score;
                }
                if (a.remainderLength !== b.remainderLength) {
                    return a.remainderLength - b.remainderLength;
                }
                return a.command.label.localeCompare(b.command.label);
            });

            const orderedCommands = [];
            for (let i = 0; i < scoredMatches.length; i += 1) {
                orderedCommands.push(scoredMatches[i].command);
            }
            return orderedCommands;
        };

        const openCommandAt = function(index) {
            if (index < 0 || index >= filteredCommands.length) {
                return;
            }
            const command = filteredCommands[index];
            if (command && command.href) {
                modalInstance.hide();
                window.location.href = command.href;
            }
        };

        const prepareForOpen = function() {
            resetResults();
            showEmptyState('Start typing to search.');
        };

        const openPalette = function() {
            prepareForOpen();
            modalInstance.show();
        };

        if (toggleButton) {
            toggleButton.addEventListener('click', function(event) {
                event.preventDefault();
                const navbarToggle = document.getElementById('navbarToggle');
                if (navbarToggle && navbarToggle.classList.contains('show')) {
                    const existingCollapse = bootstrap.Collapse.getInstance(navbarToggle);
                    if (existingCollapse) {
                        existingCollapse.hide();
                    } else {
                        new bootstrap.Collapse(navbarToggle, { toggle: false }).hide();
                    }
                }
                openPalette();
            });
        }

        document.addEventListener('keydown', function(event) {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                openPalette();
            }
        });

        modalElement.addEventListener('shown.bs.modal', function() {
            window.requestAnimationFrame(function() {
                inputElement.focus();
                inputElement.select();
            });
        });

        modalElement.addEventListener('hidden.bs.modal', function() {
            inputElement.value = '';
            resetResults();
            hideEmptyState();
        });

        inputElement.addEventListener('input', function() {
            const rawQuery = inputElement.value || '';
            const query = rawQuery.trim().toLowerCase();
            searchSequence += 1;
            const currentToken = searchSequence;

            if (!query) {
                resetResults();
                showEmptyState('Start typing to search.');
                return;
            }

            showEmptyState('Searching...');
            window.requestAnimationFrame(function() {
                if (currentToken !== searchSequence) {
                    return;
                }
                const allCommands = ensureCommands();
                const nextResults = filterCommands(allCommands, query);
                if (currentToken !== searchSequence) {
                    return;
                }
                filteredCommands = nextResults;
                renderResults(filteredCommands, query);
            });
        });

        inputElement.addEventListener('keydown', function(event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (filteredCommands.length) {
                    const nextIndex = activeIndex === -1 ? 0 : Math.min(activeIndex + 1, filteredCommands.length - 1);
                    setActiveResult(nextIndex, false);
                }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (filteredCommands.length) {
                    const prevIndex = activeIndex <= 0 ? 0 : activeIndex - 1;
                    setActiveResult(prevIndex, false);
                }
            } else if (event.key === 'Enter') {
                event.preventDefault();
                if (filteredCommands.length > 0) {
                    const targetIndex = activeIndex === -1 ? 0 : activeIndex;
                    openCommandAt(targetIndex);
                }
            } else if (event.key === 'Escape') {
                modalInstance.hide();
            }
        });

        resultsContainer.addEventListener('click', function(event) {
            const target = event.target.closest ? event.target.closest('[data-command-index]') : null;
            if (!target) {
                return;
            }
            const index = parseInt(target.getAttribute('data-command-index'), 10);
            if (!isNaN(index)) {
                openCommandAt(index);
            }
        });

        resultsContainer.addEventListener('keydown', function(event) {
            const items = resultsContainer.querySelectorAll('[data-command-index]');
            if (!items.length) {
                return;
            }
            const currentIndex = Array.prototype.indexOf.call(items, event.target);
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                const nextIndex = currentIndex + 1 >= items.length ? currentIndex : currentIndex + 1;
                setActiveResult(nextIndex);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (currentIndex <= 0) {
                    inputElement.focus();
                } else {
                    setActiveResult(currentIndex - 1);
                }
            } else if (event.key === 'Enter') {
                event.preventDefault();
                openCommandAt(currentIndex);
            } else if (event.key === 'Escape') {
                modalInstance.hide();
            }
        });

        schedulePreload();
    };

    prefetchMiscReportCommands() {
        const self = this;
        const isAuthenticated = this.determineAuthenticationState();
        if (isAuthenticated === false) {
            console.info('Quick Find: Skipping misc report preload for logged out users.');
            return;
        }
        const cachedDefinitions = window.__miscReportDefinitions;
        if (Array.isArray(cachedDefinitions) && cachedDefinitions.length) {
            this.miscReportCommands = this.buildMiscReportCommands(cachedDefinitions);
            if (typeof self._invalidateCommandCache === 'function') {
                self._invalidateCommandCache();
            }
            return;
        }
        if (typeof window.fetch !== 'function') {
            return;
        }
        fetch('/core/api/misc-report-types/', { credentials: 'same-origin' })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    const error = new Error('User not authenticated');
                    error.code = 'NOT_AUTHENTICATED';
                    throw error;
                }
                if (!response.ok) {
                    throw new Error('Request failed with status ' + response.status);
                }
                const contentType = response.headers && response.headers.get ? response.headers.get('content-type') : '';
                if (contentType && contentType.indexOf('application/json') === -1) {
                    const error = new Error('Unexpected response type: ' + contentType);
                    error.code = 'UNEXPECTED_CONTENT_TYPE';
                    throw error;
                }
                return response.json();
            })
            .then(function(payload) {
                const reports = Array.isArray(payload && payload.reports) ? payload.reports : [];
                if (!reports.length) {
                    return;
                }
                window.__miscReportDefinitions = reports.slice();
                self.miscReportCommands = self.buildMiscReportCommands(reports);
                if (typeof self._invalidateCommandCache === 'function') {
                    self._invalidateCommandCache();
                }
            })
            .catch(function(error) {
                if (error && (error.code === 'NOT_AUTHENTICATED' || (error.message && error.message.indexOf('Not authenticated') > -1))) {
                    console.info('Quick Find: Misc report preload is unavailable until the user logs in.');
                    return;
                }
                if (error && error.code === 'UNEXPECTED_CONTENT_TYPE') {
                    console.warn('Quick Find: Received non-JSON response while loading misc reports, skipping preload.');
                    return;
                }
                if (error instanceof SyntaxError) {
                    console.warn('Quick Find: Misc report payload was not valid JSON, skipping preload.');
                    return;
                }
                console.error('Failed to preload misc reports for Quick Find:', error);
            });
    };

    buildMiscReportCommands(definitions) {
        if (!Array.isArray(definitions)) {
            return [];
        }
        const commands = [];
        for (let i = 0; i < definitions.length; i += 1) {
            const definition = definitions[i];
            if (!definition) {
                continue;
            }
            const slug = definition.slug || '';
            const label = definition.label || slug;
            if (!slug || !label) {
                continue;
            }
            const href = definition.direct_url || '/core/reports?report=' + encodeURIComponent(slug);
            const groupLabel = 'Misc. Reports';
            commands.push({
                label: label,
                href: href,
                groupLabel: groupLabel,
                labelLower: label.toLowerCase(),
                groupLower: groupLabel.toLowerCase(),
                keywordsLower: []
            });
        }
        return commands;
    };

    registerCommandPaletteEntries(entries) {
        if (!Array.isArray(entries) || !entries.length) {
            return;
        }

        if (!Array.isArray(this.externalCommandPaletteEntries)) {
            this.externalCommandPaletteEntries = [];
        }

        const normalizeKeywords = function(entry) {
            const keywords = [];
            if (Array.isArray(entry.keywordsLower)) {
                for (let i = 0; i < entry.keywordsLower.length; i += 1) {
                    const existingKeyword = entry.keywordsLower[i];
                    if (typeof existingKeyword === 'string') {
                        const trimmed = existingKeyword.trim().toLowerCase();
                        if (trimmed) {
                            keywords.push(trimmed);
                        }
                    }
                }
            }
            if (Array.isArray(entry.keywords)) {
                for (let i = 0; i < entry.keywords.length; i += 1) {
                    const keyword = entry.keywords[i];
                    if (typeof keyword === 'string') {
                        const trimmedKeyword = keyword.trim().toLowerCase();
                        if (trimmedKeyword) {
                            keywords.push(trimmedKeyword);
                        }
                    }
                }
            }
            const uniqueKeywords = [];
            const keywordSet = new Set();
            for (let i = 0; i < keywords.length; i += 1) {
                const k = keywords[i];
                if (!keywordSet.has(k)) {
                    keywordSet.add(k);
                    uniqueKeywords.push(k);
                }
            }
            return uniqueKeywords;
        };

        const existingKeys = new Set();
        for (let i = 0; i < this.externalCommandPaletteEntries.length; i += 1) {
            const existing = this.externalCommandPaletteEntries[i];
            if (existing && existing.label && existing.href) {
                existingKeys.add(existing.label + '|' + existing.href);
            }
        }

        let didRegister = false;
        for (let i = 0; i < entries.length; i += 1) {
            const entry = entries[i];
            if (!entry || typeof entry.label !== 'string' || typeof entry.href !== 'string') {
                continue;
            }
            const label = entry.label.trim();
            const href = entry.href.trim();
            if (!label || !href) {
                continue;
            }
            const groupLabel = entry.groupLabel ? entry.groupLabel.trim() : '';
            const key = label + '|' + href;
            if (existingKeys.has(key)) {
                continue;
            }
            const normalizedEntry = {
                label: label,
                href: href,
                groupLabel: groupLabel,
                labelLower: (entry.labelLower && typeof entry.labelLower === 'string') ? entry.labelLower : label.toLowerCase(),
                groupLower: groupLabel ? ((entry.groupLower && typeof entry.groupLower === 'string') ? entry.groupLower : groupLabel.toLowerCase()) : '',
                keywordsLower: normalizeKeywords(entry)
            };
            this.externalCommandPaletteEntries.push(normalizedEntry);
            existingKeys.add(key);
            didRegister = true;
        }

        if (didRegister && typeof this._invalidateCommandCache === 'function') {
            this._invalidateCommandCache();
        }
    };

    buildProductionScheduleCommandEntries() {
        const entries = [];
        const baseHref = '/prodverse/production-schedule/';
        const groupLabel = 'Production Schedules';
        const schedules = [
            { param: 'inline', label: 'Inline Schedule' },
            { param: 'pd', label: 'PD Line Schedule' },
            { param: 'jb', label: 'JB Line Schedule' },
            { param: 'horix', label: 'Horix Schedule' },
            { param: 'blister', label: 'Blister Schedule', keywords: ['let blister schedule', 'let blister', 'let'] },
            { param: 'oil', label: 'Oil Line Schedule' },
            { param: 'pouch', label: 'Pouch Room 1 Schedule' },
            { param: 'kit', label: 'Kit Lines Schedule', keywords: ['let kit schedule', 'let kit', 'let'] }
        ];

        for (let i = 0; i < schedules.length; i += 1) {
            const schedule = schedules[i];
            if (!schedule || !schedule.param || !schedule.label) {
                continue;
            }
            const href = `${baseHref}?line=${encodeURIComponent(schedule.param)}`;
            entries.push({
                label: schedule.label,
                href: href,
                groupLabel: groupLabel,
                keywords: Array.isArray(schedule.keywords) ? schedule.keywords : []
            });
        }

        return entries;
    };

    buildCommandPaletteEntries() {
        const navBar = document.getElementById('theNavBar');
        if (!navBar) {
            return [];
        }

        const anchors = navBar.querySelectorAll('a[href]:not([data-command-ignore])');
        const seen = {};
        const commands = [];

        for (let i = 0; i < anchors.length; i += 1) {
            const anchor = anchors[i];
            const href = anchor.getAttribute('href');

            if (!href || href === '#' || href.indexOf('javascript:') === 0) {
                continue;
            }

            const rawLabel = (anchor.dataset && anchor.dataset.commandLabel) ? anchor.dataset.commandLabel : anchor.textContent;
            const label = rawLabel ? rawLabel.replace(/\s+/g, ' ').trim() : '';

            if (!label) {
                continue;
            }

            const key = label + '|' + href;
            if (seen[key]) {
                continue;
            }

            let groupLabel = '';
            let parentMenu = null;
            if (anchor.closest) {
                parentMenu = anchor.closest('.dropdown-menu');
            }
            if (parentMenu && parentMenu.previousElementSibling) {
                const toggle = parentMenu.previousElementSibling;
                const toggleText = (toggle.dataset && toggle.dataset.commandLabel) ? toggle.dataset.commandLabel : toggle.textContent;
                if (toggleText) {
                    groupLabel = toggleText.replace(/\s+/g, ' ').trim();
                }
            }

            commands.push({
                label: label,
                href: href,
                groupLabel: groupLabel,
                labelLower: label.toLowerCase(),
                groupLower: groupLabel.toLowerCase(),
                keywordsLower: []
            });
            seen[key] = true;
        }

        if (Array.isArray(this.externalCommandPaletteEntries) && this.externalCommandPaletteEntries.length) {
            for (let i = 0; i < this.externalCommandPaletteEntries.length; i += 1) {
                const entry = this.externalCommandPaletteEntries[i];
                if (!entry || !entry.label || !entry.href) {
                    continue;
                }
                const key = entry.label + '|' + entry.href;
                if (seen[key]) {
                    continue;
                }
                const groupLabel = entry.groupLabel || '';
                const labelLower = entry.labelLower || entry.label.toLowerCase();
                const groupLower = groupLabel ? (entry.groupLower || groupLabel.toLowerCase()) : '';
                const keywordsLower = Array.isArray(entry.keywordsLower) ? entry.keywordsLower.slice() : [];
                commands.push({
                    label: entry.label,
                    href: entry.href,
                    groupLabel: groupLabel,
                    labelLower: labelLower,
                    groupLower: groupLower,
                    keywordsLower: keywordsLower
                });
                seen[key] = true;
            }
        }

        if (Array.isArray(this.miscReportCommands) && this.miscReportCommands.length) {
            for (let i = 0; i < this.miscReportCommands.length; i += 1) {
                const miscCommand = this.miscReportCommands[i];
                if (!miscCommand || !miscCommand.label || !miscCommand.href) {
                    continue;
                }
                const miscKey = miscCommand.label + '|' + miscCommand.href;
                if (seen[miscKey]) {
                    continue;
                }
                const groupLabel = miscCommand.groupLabel || 'Misc. Reports';
                const labelLower = miscCommand.labelLower || miscCommand.label.toLowerCase();
                const groupLower = miscCommand.groupLower || groupLabel.toLowerCase();
                const keywordsLower = Array.isArray(miscCommand.keywordsLower) ? miscCommand.keywordsLower.slice() : [];
                commands.push({
                    label: miscCommand.label,
                    href: miscCommand.href,
                    groupLabel: groupLabel,
                    labelLower: labelLower,
                    groupLower: groupLower,
                    keywordsLower: keywordsLower
                });
                seen[miscKey] = true;
            }
        }

        commands.sort(function(a, b) {
            return a.label.localeCompare(b.label);
        });

        return commands;
    };
      
};

export class DeskSchedulePage {
    constructor() {
        try {
            if (!window.location.href.includes("all")){
                this.setupDragnDrop();
            };
            this.setupEventListeners();
            this.addHxLotNumbers();
        } catch(err) {
            console.error(err.message);
        };
    };


    setupDragnDrop(){
        // this function posts the current order on the page to the database
        function updateScheduleOrder(){
            let deskScheduleDict = {};
            let thisRow;
            $('#deskScheduleTable tbody tr').each(function() {
                thisRow = $(this);
                let orderNumber = $(this).find('td.orderCell').text();
                let lotNumber = $(this).find('td.lot-number-cell').attr('lot-number');
                // Skip rows with an empty value in the second cell.
                if (lotNumber.trim() !== '') {
                    deskScheduleDict[lotNumber] = orderNumber;
                }
            });
            if (thisRow.hasClass('Desk_1')) {
                deskScheduleDict["desk"] = "Desk_1";
            } else if (thisRow.hasClass('Desk_2')) {
                deskScheduleDict["desk"] = "Desk_2";
            } else if (thisRow.hasClass('LET_Desk')) {
                deskScheduleDict["desk"] = "LET_Desk";
            }
            let jsonString = JSON.stringify(deskScheduleDict);
            let encodedDeskScheduleOrder = btoa(jsonString);
            let scheduleUpdateResult;
            $.ajax({
                url: `/core/update-desk-order?encodedDeskScheduleOrder=${encodedDeskScheduleOrder}`,
                async: false,
                dataType: 'json',
                success: function(data) {
                    scheduleUpdateResult = data;
                    console.log(data)
                }
            });
        };

        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#deskScheduleTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0) {
                            $(this).find("td").eq(0).html(index); // Set Order column cell = index value
                        }
                    });
                    updateScheduleOrder();
                }
            });
        });
    };

    setupEventListeners() {
        $(".tankSelect").change(function() {
            const $this = $(this);
            const $row = $this.closest('tr');
            
            // 🎯 Enhanced: Use data-blend-id for more reliable identification
            const blendId = $row.attr('data-blend-id');
            const lotNumber = $row.find('.lot-number-cell').attr('lot-number') || $row.find('td:eq(4)').text().trim();
            const tank = $this.val();
            const blendArea = new URL(window.location.href).searchParams.get("blend-area");
            
            console.log(`🚰 Tank selection changed: blend_id=${blendId}, lot=${lotNumber}, tank=${tank}, area=${blendArea}`);
            
            // Encode parameters for backend
            const encodedLotNumber = btoa(lotNumber);
            const encodedTank = btoa(tank);
            
            // Add visual feedback during update
            $this.css({
                'backgroundColor': '#fff3cd',
                'transition': 'background-color 0.3s ease'
            });
            
            $.ajax({
                url: `/core/update-scheduled-blend-tank?encodedLotNumber=${encodedLotNumber}&encodedTank=${encodedTank}&blendArea=${blendArea}`,
                type: 'GET',
                dataType: 'json',
                success: function(data) {
                    console.log(`✅ Tank update successful:`, data);
                    
                    // Clear visual feedback on success
                    setTimeout(() => {
                        $this.css('backgroundColor', '');
                    }, 1000);
                    
                    // Note: WebSocket will handle updating other users' views
                    // No need for optimistic updates here
                },
                error: function(xhr, status, error) {
                    console.error(`❌ Tank update failed:`, error);
                    
                    // Revert selection on error
                    $this.val($this.data('previous-value') || '');
                    
                    // Show error feedback
                    $this.css('backgroundColor', '#ffcccc');
                    setTimeout(() => {
                        $this.css('backgroundColor', '');
                    }, 2000);
                    
                    alert(`Failed to update tank assignment: ${error}`);
                }
            });
        });
        
        // 🎯 Store previous value for error recovery
        $(".tankSelect").on('focus', function() {
            $(this).data('previous-value', $(this).val());
        });
    };
    addHxLotNumbers() {
        
    };

};

export class ItemsByAuditGroupPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners(){
        this.setupEditModalHandlers();
        this.setupFilterFormHandlers();
    }

    setupEditModalHandlers() {
        const editButtons = document.querySelectorAll('.editAuditGroupButton');
        if (!editButtons.length) {
            return;
        }

        const recordIdInput = document.getElementById('auditGroupRecordId');
        const itemCodeInput = document.getElementById('id_item_code');
        const descriptionInput = document.getElementById('id_item_description');
        const auditGroupSelect = document.getElementById('id_audit_group');
        const countingUnitSelect = document.getElementById('id_counting_unit');
        const itemTypeSelect = document.getElementById('id_item_type');
        const modalTitle = document.getElementById('editAuditGroupItemModalLabel');

        editButtons.forEach((button) => {
            button.addEventListener('click', () => {
                if (recordIdInput) {
                    recordIdInput.value = button.dataset.itemId || '';
                }
                if (itemCodeInput) {
                    itemCodeInput.value = button.dataset.itemCode || '';
                    itemCodeInput.readOnly = true;
                }
                if (descriptionInput) {
                    descriptionInput.value = button.dataset.itemDescription || '';
                    descriptionInput.readOnly = true;
                }
                if (auditGroupSelect) {
                    auditGroupSelect.value = button.dataset.auditGroup || '';
                }
                if (countingUnitSelect) {
                    countingUnitSelect.value = button.dataset.countingUnit || '';
                }
                if (itemTypeSelect) {
                    itemTypeSelect.value = button.dataset.itemType || '';
                }
                if (modalTitle) {
                    const code = button.dataset.itemCode || 'Item';
                    modalTitle.textContent = `Edit ${code}`;
                }
            });
        });
    }

    setupFilterFormHandlers() {
        const filterForm = document.getElementById('auditGroupFilterForm');
        if (!filterForm) {
            return;
        }

        ['auditGroupLinks'].forEach((fieldId) => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('change', () => filterForm.submit());
            }
        });
    }
};

export class CountCollectionLinksPage {
    constructor(thisCountCollectionWebSocket) {
        try {
            this.setupEventListeners(thisCountCollectionWebSocket);
            this.setupDragnDrop(thisCountCollectionWebSocket);
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners(thisCountCollectionWebSocket) {
        const renameTimers = new Map();
        const DEBOUNCE_INTERVAL_MS = 500;

        const commitRename = (inputElement) => {
            if (!inputElement) {
                return;
            }
            const collectionId = inputElement.getAttribute("collectionlinkitemid");
            if (!collectionId) {
                return;
            }
            const newName = inputElement.value;
            if (inputElement.dataset && inputElement.dataset.lastSentValue === newName) {
                return;
            }
            if (inputElement.dataset) {
                inputElement.dataset.lastSentValue = newName;
            }
            thisCountCollectionWebSocket.updateCollection(collectionId, newName);
        };

        const attachRenameHandlers = (element) => {
            if (!element || element.tagName !== 'INPUT') {
                return;
            }
            if (element.dataset && element.dataset.renameHandlerAttached === 'true') {
                return;
            }
            if (element.dataset) {
                element.dataset.renameHandlerAttached = 'true';
                element.dataset.lastSentValue = element.value;
            }

            const collectionId = element.getAttribute("collectionlinkitemid");
            element.addEventListener("input", () => {
                if (!collectionId) {
                    return;
                }
                if (renameTimers.has(collectionId)) {
                    clearTimeout(renameTimers.get(collectionId));
                }
                renameTimers.set(collectionId, setTimeout(() => {
                    renameTimers.delete(collectionId);
                    commitRename(element);
                }, DEBOUNCE_INTERVAL_MS));
            });

            element.addEventListener("blur", () => {
                if (!collectionId) {
                    return;
                }
                if (renameTimers.has(collectionId)) {
                    clearTimeout(renameTimers.get(collectionId));
                    renameTimers.delete(collectionId);
                }
                commitRename(element);
            });
        };

        const enableDeleteButton = (buttonElement) => {
            if (!buttonElement) {
                return;
            }
            buttonElement.removeAttribute("disabled");
            buttonElement.classList.remove("disabled");
        };

        document.querySelectorAll(".collectionNameElement").forEach(attachRenameHandlers);
        document.querySelectorAll(".collectionIdButton").forEach(buttonElement => {
            buttonElement.addEventListener("click",function(){
                const thisCollectionItemId = buttonElement.getAttribute("collectionlinkitemid");
                const thisCollectionIdInput = $(`input[collectionlinkitemid=${thisCollectionItemId}]`);
                let result = updateCountCollection(thisCollectionItemId, thisCollectionIdInput.val());
                console.log(result);
                buttonElement.setAttribute("style", "display:none;");
            });
        });
        document.querySelectorAll(".deleteCountLinkButton").forEach(deleteButton => {
            enableDeleteButton(deleteButton);
            deleteButton.addEventListener("click",function(){
                const collectionId = deleteButton.getAttribute("collectionlinkitemid");
                thisCountCollectionWebSocket.deleteCollection(collectionId);
            });
        });

        const observer = new MutationObserver(function(mutationsList) {
            for (let mutation of mutationsList) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(addedNode => {
                        if (addedNode.nodeType === 1 && addedNode.matches('.tableBodyRow')) {
                            const renameInput = addedNode.querySelector('input.collectionNameElement');
                            if (renameInput) {
                                attachRenameHandlers(renameInput);
                            }
                            const deleteButton = addedNode.querySelector('.deleteCountLinkButton');
                            if (deleteButton) {
                                enableDeleteButton(deleteButton);
                                deleteButton.addEventListener("click", function() {
                                    const collectionId = deleteButton.getAttribute("collectionlinkitemid");
                                    thisCountCollectionWebSocket.deleteCollection(collectionId);
                                });
                            }
                        }
                    });
                }
            }
        });

        observer.observe(document.querySelector('#countCollectionLinkTable tbody'), { childList: true });

    }

    setupDragnDrop(thisCountCollectionWebSocket){
        // this function posts the current order on the page to the database
        function updateCollectionLinkOrder(){
            let collectionLinkDict = {};
            $('#countCollectionLinkTable tbody tr').each(function() {
                let orderNumber = $(this).find('td:eq(0)').text();
                let collectionID = $(this).find('td:eq(1)').attr('data-collection-id');
                // Skip rows with an empty value in the second cell.
                if (collectionID.trim() !== '') {
                    collectionLinkDict[collectionID] = orderNumber;
                }
            });
            thisCountCollectionWebSocket.updateCollectionOrder(collectionLinkDict);
        };

        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#countCollectionLinkTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0) {
                            $(this).find("td").eq(0).html(index); // Set Order column cell = index value
                        }
                    });
                    updateCollectionLinkOrder();
                }
            });

        });
    };
    
};

export class CountReportPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
            console.log("Error", err.stack);
            console.log("Error", err.name);
            console.log("Error", err.message);
        };
    };
};

export class BlendInstructionEditorPage {
    constructor() {
        try {
            this.setupDragnDrop();
            this.setupEventListeners();
            this.setReadOnlyFields();
            this.setupFormMonitoring();
        } catch(err) {
            console.error(err.message);
        };
    };


    setupDragnDrop(){
        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#blendInstructionTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0 && !($(this).attr('id') === 'addNewInstructionRow')) {
                            $(this).find("td").eq(0).find('input').val(index); // Set Order column cell = index value
                        }
                    });
                    updateBlendInstructionsOrder();
                }
            });
        });
    };

    setupEventListeners(){
        document.getElementById("addNewInstructionButton").addEventListener('click', function(e){
            e.preventDefault();
            const encodedItemCode = getURLParameter("itemCode");
            const newBlendInstructionInfo = getNewBlendInstructionInfo(encodedItemCode);
            console.log(newBlendInstructionInfo)

            // Get the formset's total forms input element and obtain the form count
            let totalForms = document.querySelector('input[name="form-TOTAL_FORMS"]');
            let formNum = parseInt(totalForms.value);
            
            // // Get the last form in the formset, which is the second to last row in the 
            // // table due to the row containing the Add New button.
            let table = document.getElementById("blendInstructionTable");
            let rows = table.tBodies[0].children;
            let secondToLastRow = rows[rows.length - 2];
            let newRow = secondToLastRow.cloneNode(true);

            // // Update the new form's input elements to use the new form count
            newRow.querySelectorAll('input, select, textarea').forEach(function(input) {
                input.name = input.name.replace('-' + (formNum - 1) + '-', '-' + formNum + '-');
                input.id = input.id.replace('-' + (formNum - 1) + '-', '-' + formNum + '-');
            });
            newRow.querySelectorAll('td').forEach(function(tdCell) {
                tdCell.setAttribute('data-item-id', newBlendInstructionInfo.next_id) 
            })
            
            newRow.querySelector('input[name*="step_number"]').value = formNum + 1;
            newRow.querySelector('input[name*="step_description"]').value = "";
            newRow.querySelector('input[name*="component_item_code"]').value = "";
            newRow.querySelector('input[name*="id"]').value = newBlendInstructionInfo.next_id;
            newRow.querySelector('.deleteBtn').setAttribute('data-item-id', newBlendInstructionInfo.next_id)


            let lastRow = table.tBodies[0].lastElementChild;

            // Insert the new form before the "Add New" button row
            lastRow.parentNode.insertBefore(newRow, document.getElementById('addNewInstructionRow'));

            // Increment the form count
            totalForms.value = formNum + 1;

            // console.log();
        })
    }

    setReadOnlyFields() {
        $('input[name*="step_number"]').prop('readonly', true); 
        $('input[name*="step_number"]').css('pointer-events', 'none');
    }

    setupFormMonitoring(){
        let formIsDirty = false;
        document.querySelector('form').addEventListener('input', function () {
            formIsDirty = true;
        });

        document.querySelector('#saveInstructionsButton').addEventListener('click', function () {
            formIsDirty = false;
        });

        window.addEventListener('beforeunload', function (e) {
            if (formIsDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
};

export class PartialContainerLabelPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $("#label-container-type-dropdown").on('change', function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code").css({"color": "", "font-weight": ""});
            let selectedContainerWeight = this.value;
            let selectedContainerType = $("#label-container-type-dropdown option:selected").text()
            if (selectedContainerWeight == "CUSTOM") {
                $("#custom-tare-container").show();
                $("#inventory-label-container-weight").css("color", "red").css("font-weight", "bold").text("Enter container weight.");
                $("#inventory-label-container-type").css("color", "").css("font-weight", "").text(selectedContainerType);
            } else {
                $("#custom-tare-container").hide();
                $("#inventory-label-container-weight").css("color", "").css("font-weight", "").text(selectedContainerWeight);
                $("#inventory-label-container-type").css("color", "").css("font-weight", "").text(selectedContainerType);
            }
            if ($("#gross-weight").val()) {
                let grossWeight = $("#gross-weight").val();
                let tareWeight = $("#inventory-label-container-weight").text();
                netWeight = (grossWeight - tareWeight)
                $("#net-weight").text(netWeight + " lbs.");
                let itemCode = $("#inventory-label-item-code").text();
                updateVolume(netWeight, itemCode)
            }
        });

        $("#gross-weight").keyup(function(e) {
            $(".error-message").each(function() {
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code").css({"color": "", "font-weight": ""});
            let grossWeight = this.value;
            let tareWeight = $("#inventory-label-container-weight").text();
            let itemCode = $("#inventory-label-item-code").text();
            if (!tareWeight) {
                $("#inventory-label-container-type").css("color", "red").css("font-weight", "bold").text("Please select container.");
            } else {
                // $("#inventory-label-container-type").css("color", "").text($("#label-container-type-dropdown option:selected").text());
                let netWeight = grossWeight - tareWeight
                $("#net-weight").text(netWeight + " lbs.");
                updateVolume(netWeight, itemCode);
            }
            
            // $("#net-weight").text(grossWeight);
        });

        $("#custom-tare-weight").keyup(function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});
            let tareWeight = this.value;
            $("#inventory-label-container-weight").css("color", "").css("font-weight", "").text(tareWeight);
        });

        function updateVolume(netWeight, itemCode) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});
            let itemInfo = getItemInfo(itemCode, "itemCode");
            let shipWeight = itemInfo.shipweight;
            let standardUOM = itemInfo.standardUOM;

            if (!shipWeight) {
                $("#net-gallons").text("N/A");
            } else {
                $("#net-gallons").text((netWeight / shipWeight).toFixed(2) + " gal");
            }
           
        }
        $("#initialsField").css("text-transform", "uppercase");
        $("#initialsField").click(function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});

        })
        
        $("#blendLabelPrintButton").click(function(e) {
            let hasError = false;
            let grossWeight = $("#gross-weight").val();
            let containerType = $("#inventory-label-container-type").text();
            let itemCode = $("#inventory-label-item-code").text();
            let initials = $("#initialsField").val();

            // Reset previous error states
            $(".error-message").remove();
            $("#gross-weight, #label-container-type-dropdown").css({"color": "", "font-weight": ""});

            if (!grossWeight) {
                $("#gross-weight").after('<div class="error-message" style="color: red; font-weight: bold;">Please enter weight.</div>');
                $("#gross-weight").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!initials) {
                $("#initialsField").after('<div class="error-message" style="color: red; font-weight: bold;">Please initial.</div>');
                $("#initialsField").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!containerType) { // Replace 'defaultOptionValue' with your actual default option value if any
                $("#inventory-label-container-type").after('<div class="error-message" style="color: red; font-weight: bold;">Please select container type.</div>');
                $("#inventory-label-container-type").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!itemCode) { // Replace 'defaultOptionValue' with your actual default option value if any
                $("#inventory-label-item-code").after('<div class="error-message" style="color: red; font-weight: bold;">Please enter item code.</div>');
                $("#inventory-label-item-code").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (hasError) {
                e.preventDefault(); // Prevent form submission if there are errors
            } else {
                let encodedItemCode = btoa(itemCode);
                logContainerLabelPrint(encodedItemCode);
            }
            
        });
        // Place this code in a suitable location within your script, such as inside a constructor or initialization function

        // Select the target node
        let target = document.getElementById('inventory-label-item-description');

        // Create an observer instance
        let observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                let itemDescription = mutation.target.textContent;
                let itemCode = $("#inventory-label-item-code").text();
                let itemInfo = getItemInfo(itemCode, "itemCode");
                let shipWeight = itemInfo.shipweight;
                let standardUOM = itemInfo.standardUOM;
                if (itemDescription.startsWith("BLEND")) {
                    $("#label-container-select-row").hide();
                    $("#custom-tare-container").hide();
                    $("#custom-tare-container").hide();
                    $("#containerTypeRow").hide();
                    $("#containerWeightRow").hide();
                    $("#grossWeightRow").hide();
                    $("#netWeightRow").hide();
                    $("#inputHolderTable")
                    $("#net-gallons").html('<input type="text" id="net-gallons-input" name="net_gallons" value="" />');
                } else {
                    $("#label-container-select-row").show();
                    $("#custom-tare-container").show();
                    $("#custom-tare-container").show();
                    // $("#containerTypeRow").show();
                    $("#containerWeightRow").show();
                    $("#grossWeightRow").show();
                    $("#netWeightRow").show();
                    $("#net-gallons-input").remove();
                };
            });
        });

        // Configuration of the observer--????:
        var config = { characterData: true, childList: true, subtree: true };
        // Pass in the target node, as well as the observer options
        observer.observe(target, config);

        // Later, you can stop observing
        // observer.disconnect();

    };
};

export class MissingAuditGroupPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $(".discardButton").click(function(e) {
            e.preventDefault(); // Prevent the default event
            $(this).parent().parent().remove(); // Remove the grandparent element
        });
    };
};

export class ListToCountListPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $("#listField").keyup(function(e) {
            // Clear existing table content
            $("#itemTable tbody").empty();
            
            // Split the input by newlines
            var lines = $(this).val().split('\n');
            
            // Create table rows for each non-empty line
            lines.forEach(function(line) {
                if (line.trim() !== '') {
                    var newRow = $("<tr>");
                    var checkboxCell = $("<td>").append(
                        $("<input>")
                            .attr("type", "checkbox")
                            .prop("checked", true)
                    );
                    var contentCell = $("<td>").text(line.trim());
                    
                    newRow.append(checkboxCell).append(contentCell);
                    $("#itemTable tbody").append(newRow);
                }
            });
        });
    };
};

export class FlushToteLabelPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $("#label-line-dropdown").change(function() {
            $("#flush-label-line").text($("#label-line-dropdown").val());
            $("#flush-label-flush-type").text($("#id_flush_tote_type").val());
        });
        $("#id_flush_tote_type").change(function() {
            $("#flush-label-line").text($("#label-line-dropdown").val());
            $("#flush-label-flush-type").text($("#id_flush_tote_type").val());
        });
    }
}


export class BomCostToolPage {
    constructor() {
        this.API_URL = '/core/api/bom-cost/';
        this.warehouse = 'MTG';
        this.calcBtn = document.getElementById('calcBtn');
        this.itemInput = document.getElementById('itemCode');
        this.qtyInput = document.getElementById('qty');
        this.resultsEl = document.getElementById('results');
        this.alertEl = document.getElementById('alert');
        this.costFileInput = document.getElementById('costFile');
        this.costFileStatus = document.getElementById('costFileStatus');
        this.resetCostFileBtn = document.getElementById('resetCostFile');
        this.isLoading = false;

        try {
            this.bindEvents();
            this.updateCostFileStatus();
        } catch (err) {
            console.error(err.message);
        }
    }

    bindEvents() {
        if (this.calcBtn) {
            this.calcBtn.addEventListener('click', () => this.runCalc());
        }

        [this.itemInput, this.qtyInput].forEach(input => {
            if (!input) return;
            input.addEventListener('keypress', evt => {
                if (evt.key === 'Enter') {
                    evt.preventDefault();
                    this.runCalc();
                }
            });
        });

        if (this.costFileInput) {
            this.costFileInput.addEventListener('change', () => this.updateCostFileStatus());
        }

        if (this.resetCostFileBtn) {
            this.resetCostFileBtn.addEventListener('click', () => {
                if (this.costFileInput) {
                    this.costFileInput.value = '';
                }
                this.updateCostFileStatus();
            });
        }
    }

    setLoading(state) {
        this.isLoading = state;
        if (this.calcBtn) {
            this.calcBtn.disabled = state;
            this.calcBtn.textContent = state ? 'Calculating...' : 'Calculate Cost';
        }
    }

    showAlert(message) {
        if (!this.alertEl) return;
        this.alertEl.textContent = message;
        this.alertEl.className = 'alert error';
    }

    clearAlert() {
        if (!this.alertEl) return;
        this.alertEl.textContent = '';
        this.alertEl.className = 'alert hidden';
    }

    updateCostFileStatus() {
        if (!this.costFileStatus) return;
        const hasFiles = this.costFileInput && this.costFileInput.files && this.costFileInput.files.length;
        if (hasFiles) {
            this.costFileStatus.textContent = `Override ready: ${this.costFileInput.files[0].name}`;
        } else {
            this.costFileStatus.textContent = 'Using server workbook.';
        }
    }

    async runCalc() {
        if (this.isLoading) return;

        const itemCode = (this.itemInput?.value || '').trim().toUpperCase();
        const quantity = parseFloat(this.qtyInput?.value || '');
        const overrideFile = this.costFileInput?.files?.[0];

        if (!itemCode) {
            this.showAlert('Please enter an item code.');
            return;
        }

        if (!Number.isFinite(quantity) || quantity <= 0) {
            this.showAlert('Quantity must be greater than zero.');
            return;
        }

        this.setLoading(true);
        this.clearAlert();

        try {
            let response;
            if (overrideFile) {
                const csrfToken = this.getCsrfToken();
                if (!csrfToken) {
                    this.showAlert('Missing CSRF token. Open this tool from the main app to upload workbooks.');
                    this.setLoading(false);
                    return;
                }

                const formData = new FormData();
                formData.append('item_code', itemCode);
                formData.append('quantity', quantity);
                formData.append('warehouse', this.warehouse);
                formData.append('cost_override', overrideFile);

                response = await fetch(this.API_URL, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'same-origin',
                    body: formData,
                });
            } else {
                const params = new URLSearchParams({
                    item_code: itemCode,
                    quantity: quantity,
                    warehouse: this.warehouse,
                });

                response = await fetch(`${this.API_URL}?${params.toString()}`, {
                    headers: { 'Accept': 'application/json' },
                    credentials: 'same-origin',
                });
            }

            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.error || 'Unable to calculate cost.');
            }

            this.renderResults(payload);
        } catch (error) {
            this.showAlert(error.message || 'Unexpected error occurred.');
            if (this.resultsEl) {
                this.resultsEl.innerHTML = '';
            }
        } finally {
            this.setLoading(false);
        }
    }

    formatCurrency(value, minimumFractionDigits = 2, maximumFractionDigits = 2) {
        const numberValue = Number(value) || 0;
        return numberValue.toLocaleString(undefined, {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits,
            maximumFractionDigits,
        });
    }

    formatNumber(value, maximumFractionDigits = 4) {
        const numberValue = Number(value) || 0;
        return numberValue.toLocaleString(undefined, { maximumFractionDigits });
    }

    getCsrfToken() {
        const proxyInput = document.querySelector('#csrfProxyForm input[name="csrfmiddlewaretoken"]');
        if (proxyInput && proxyInput.value && proxyInput.value !== 'NOTPROVIDED') {
            return proxyInput.value;
        }

        const name = 'csrftoken';
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let cookie of cookies) {
            const trimmed = cookie.trim();
            if (trimmed.startsWith(`${name}=`)) {
                return trimmed.substring(name.length + 1);
            }
        }
        return null;
    }

    renderResults(data) {
        if (!this.resultsEl) return;

        if (!data || !Array.isArray(data.rows)) {
            this.resultsEl.innerHTML = '<div class="results-placeholder">No data returned.</div>';
            return;
        }

        const totalCost = this.formatCurrency(data.totalCost);
        const unitCost = this.formatCurrency(data.unitCost, 2, 4);
        const elapsed = Math.round(Number(data.elapsedMs) || 0);
        const quantity = this.formatNumber(data.requestedQuantity || 0, 4);
        const warehouse = data.warehouse === 'ALL' ? 'All Warehouses' : data.warehouse;
        const pricingSource = data.pricingSource || 'Standard costs only';

        let tableRows = '';
        data.rows.forEach(row => {
            const tagClass = row.action === 'STOCK' ? 'tag-stock'
                : row.action === 'MAKE' ? 'tag-make'
                : row.action === 'BUY' ? 'tag-buy'
                : 'tag-std';
            const rowClass = `${row.isHeader ? 'row-make-header' : ''} level-${Math.min(row.level || 0, 4)}`;
            const qty = this.formatNumber(row.qty);
            const unit = this.formatCurrency(row.unit, 2, 4);
            const ext = `${row.isHeader ? '(' : ''}${this.formatCurrency(row.ext)}${row.isHeader ? ')' : ''}`;
            const note = row.note || '';

            tableRows += `
                <tr class="${rowClass}">
                    <td>${row.item}</td>
                    <td>${row.desc || ''}</td>
                    <td><span class="tag ${tagClass}">${row.action}</span></td>
                    <td>${qty}</td>
                    <td>${unit}</td>
                    <td>${ext}</td>
                    <td style="font-size:11px; color:#4a5568;">${note}</td>
                </tr>
            `;
        });

        this.resultsEl.innerHTML = `
            <div class="result-header">
                <div>
                    <div class="result-primary">${data.itemCode || ''}</div>
                    <div class="result-secondary">${data.itemDescription || ''}</div>
                </div>
                <div class="result-meta">
                    <span>${quantity} units</span>
                    <span>${warehouse}</span>
                    <span>${pricingSource}</span>
                    <span>${elapsed} ms</span>
                </div>
            </div>
            <div class="kpi-box">
                <div class="kpi">
                    <div class="kpi-val">${totalCost}</div>
                    <div class="kpi-lbl">Total Cost</div>
                </div>
                <div class="kpi">
                    <div class="kpi-val">${unitCost}</div>
                    <div class="kpi-lbl">Unit Cost</div>
                </div>
                <div class="kpi">
                    <div class="kpi-val">${elapsed} ms</div>
                    <div class="kpi-lbl">Query Time</div>
                </div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Item / Component</th>
                            <th>Description</th>
                            <th>Action</th>
                            <th>Qty</th>
                            <th>Unit Cost</th>
                            <th>Ext Cost</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        `;
    }
}


export class ComponentCoveragePage {
    constructor(payload = {}) {
        this.projectedDatetimeCache = new Map();
        this.updateData(payload);
    }

    updateData(payload = {}) {
        this.payload = payload || {};
        this.components = this.payload.components || [];
        this.tanks = this.payload.tanks || {};
        this.render();
    }

    render() {
        this.renderSummaries();
        this.renderComponents();
        this.renderTanks();
    }

    renderSummaries() {
        this.components.forEach(component => {
            const card = document.querySelector(`[data-summary-component="${component.item_code}"]`);
            if (!card) return;

            const onHand = this.formatNumber(component.on_hand_qty, 1);
            const afterSchedule = this.formatNumber(component.scheduled_usage?.projected_on_hand_after_schedule, 1);
            const pairedRow = card.querySelector('[data-role="paired-row"]');

            const descEl = card.querySelector('[data-role="description"]');
            if (descEl) descEl.textContent = component.item_description || '';

            const blendCountEl = card.querySelector('[data-role="blend-count"]');
            if (blendCountEl) blendCountEl.textContent = (component.blends || []).length;

            const onHandEl = card.querySelector('[data-role="onhand"]');
            if (onHandEl) onHandEl.textContent = onHand;

            const afterSchedEl = card.querySelector('[data-role="after-scheduled"]');
            if (afterSchedEl) afterSchedEl.textContent = afterSchedule;

            if (afterSchedEl) {
                afterSchedEl.classList.toggle('text-danger', this.isNegative(component.scheduled_usage?.projected_on_hand_after_schedule));
            }

            const tippingEl = card.querySelector('[data-role="tipping-shortage"]');
            const tippingImg = card.querySelector('[data-role="tipping-image"]');
            const tippingCalendarEl = card.querySelector('[data-role="tipping-calendar"]');
            const tip = component.tipping_shortage;
            if (tippingEl || tippingImg) {
                const hasTip = tip && tip.trigger_onhand !== null && tip.trigger_onhand !== undefined;
                if (hasTip && tippingEl) {
                    const timeStr = tip.shortage_point !== null && tip.shortage_point !== undefined
                        ? `${this.formatNumber(tip.shortage_point, 1)} hrs`
                        : 'unknown time';
                    const deskStr = tip.trigger_desk ? `Desk ${tip.trigger_desk.replace('Desk ', '')}` : '';
                    const blendStr = tip.trigger_blend_item_code || '';
                    const lotStr = tip.trigger_lot ? `lot ${tip.trigger_lot}` : '';
                    const parts = [timeStr, deskStr, blendStr, lotStr].filter(Boolean).join(' · ');
                    const baseMessage = `Tank O drops < 8,000 at ${parts}`;
                    tippingEl.textContent = baseMessage;
                    tippingEl.style.display = '';
                    tippingEl.classList.add('text-danger');

                    if (tippingCalendarEl && tip.shortage_point !== null && tip.shortage_point !== undefined) {
                        const requestToken = `${Date.now()}-${Math.random()}`;
                        tippingCalendarEl.dataset.requestToken = requestToken;
                        tippingCalendarEl.style.display = '';
                        tippingCalendarEl.textContent = 'Translating production hours…';

                        this.getProjectedDatetime(tip.shortage_point, this.payload?.generated_at)
                            .then(projectedStr => {
                                if (tippingCalendarEl.dataset.requestToken !== requestToken) return;
                                if (projectedStr) {
                                    tippingCalendarEl.textContent = `Tank O will be able to fit a truck by ${projectedStr}`;
                                } else {
                                    tippingCalendarEl.textContent = 'Calendar time unavailable';
                                }
                            })
                            .catch(() => {
                                if (tippingCalendarEl.dataset.requestToken !== requestToken) return;
                                tippingCalendarEl.textContent = 'Calendar time unavailable';
                            });
                    } else if (tippingCalendarEl) {
                        tippingCalendarEl.style.display = 'none';
                        tippingCalendarEl.textContent = '';
                    }
                } else if (tippingEl) {
                    tippingEl.textContent = '';
                    tippingEl.style.display = 'none';
                    if (tippingCalendarEl) {
                        tippingCalendarEl.style.display = 'none';
                        tippingCalendarEl.textContent = '';
                    }
                }

                if (tippingImg) {
                    tippingImg.style.display = hasTip ? 'none' : '';
                }
            }

            if (component.paired_item_code) {
                if (pairedRow) {
                    pairedRow.classList.remove('d-none');
                    pairedRow.querySelector('[data-role="paired-onhand"]').textContent = this.formatNumber(component.paired_on_hand_qty, 1);
                }
            } else if (pairedRow) {
                pairedRow.classList.add('d-none');
            }
        });
    }

    renderComponents() {
        this.components.forEach(component => {
            const section = document.querySelector(`.component-section[data-component="${component.item_code}"]`);
            if (!section) return;

            const descEl = section.querySelector('[data-role="component-description"]');
            if (descEl) descEl.textContent = component.item_description || '';

            this.renderBlendChips(component.blends || [], section.querySelector('[data-role="blend-chips"]'));
            this.renderScheduledTable(section.querySelector('table[data-table="scheduled"] tbody'), component.scheduled_usage?.rows || []);
            this.renderShortageTable(section.querySelector('table[data-table="shortages"] tbody'), component.shortage_runs || []);
        });
    }

    renderBlendChips(blends, container) {
        if (!container) return;
        if (!blends.length) {
            container.innerHTML = '<span class="text-muted">No blends found for this component.</span>';
            return;
        }

        container.innerHTML = blends
            .map(blend => `<span class="pill">${blend.blend_item_code || ''}</span>`)
            .join('');
    }

    renderScheduledTable(tbody, rows) {
        if (!tbody) return;
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">No scheduled blends on Desk 1 or Desk 2.</td></tr>';
            this.updateTableTotal(tbody, 'scheduled', 0);
            return;
        }

        const formatQty = value => this.formatNumber(value, 2);
        const formatUsage = value => this.formatNumber(value, 2);
        const formatHours = value => this.formatNumber(value, 1);

        let totalUsage = 0;

        tbody.innerHTML = rows.map(row => `
            <tr>
                <td>${row.desk || ''}</td>
                <td>${row.blend_item_code || ''}<div class="text-muted small">${row.blend_item_description || ''}</div></td>
                <td>${row.lot_number || ''}</td>
                <td>${formatQty(row.lot_quantity)}</td>
                <td>${formatQty(row.component_qty_per_blend)}</td>
                <td class="fw-semibold ${this.isNegative(row.component_usage) ? 'text-danger' : ''}">${formatUsage(row.component_usage)}</td>
                <td class="${row.shortage_point !== null && row.shortage_point !== undefined && Number(row.shortage_point) <= 5 ? 'text-danger' : ''}">${formatHours(row.shortage_point)}</td>
            </tr>
        `).map((html, idx) => {
            const usage = Number(rows[idx].component_usage);
            if (!Number.isNaN(usage)) totalUsage += usage;
            return html;
        }).join('');

        this.updateTableTotal(tbody, 'scheduled', totalUsage);
    }

    renderShortageTable(tbody, rows) {
        if (!tbody) return;
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No open shortages for these blends.</td></tr>';
            this.updateTableTotal(tbody, 'shortages', 0);
            return;
        }

        const formatQty = value => this.formatNumber(value, 2);

        let totalUsage = 0;

        tbody.innerHTML = rows.map(row => {
            const startTime = row.start_time !== null && row.start_time !== undefined ? this.formatNumber(row.start_time, 2) + ' hrs' : '—';
            const qty = Number(row.item_run_qty);
            if (!Number.isNaN(qty)) totalUsage += qty;
            return `
                <tr>
                    <td>${row.blend_item_code || ''}<div class="text-muted small">${row.blend_item_description || ''}</div></td>
                    <td>${row.prod_line || ''}</td>
                    <td>${startTime}</td>
                    <td>${formatQty(row.item_run_qty)}</td>
                    <td class="${this.isNegative(row.component_onhand_after_run) ? 'text-danger' : ''}">${formatQty(row.component_onhand_after_run)}</td>
                </tr>
            `;
        }).join('');

        this.updateTableTotal(tbody, 'shortages', totalUsage);
    }

    getComponentByCode(itemCode) {
        if (!itemCode) return null;
        return (this.components || []).find(component => component.item_code === itemCode) || null;
    }

    getScheduledUsageForComponent(itemCode) {
        const component = this.getComponentByCode(itemCode);
        return component?.scheduled_usage?.total_component_usage ?? null;
    }

    updateTableTotal(tbody, which, totalValue) {
        // find the containing component section for scoping
        const section = tbody.closest('.component-section');
        if (!section) return;
        const placeholder = section.querySelector(`[data-total-placeholder="${which}"]`);
        if (!placeholder) return;
        placeholder.textContent = `(total: ${this.formatNumber(totalValue, 2)})`;
    }

    renderTanks() {
        // Map tanks to their related component item codes when a scheduled-usage projection is needed.
        const tankComponentMap = {
            O: '100507TANKO',
        };

        Object.entries(this.tanks || {}).forEach(([tankName, tankData]) => {
            // Support both normalized keys (e.g., "B") and legacy labels ("TANK B")
            const selectors = [
                `[data-tank-card="${tankName}"]`,
                `[data-tank-card="TANK ${tankName}"]`,
            ];
            const card = document.querySelector(selectors.join(', '));
            if (!card) return;

            const currentGallons = (tankData && typeof tankData === 'object') ? tankData.gallons : tankData;
            const maxGallons = (tankData && typeof tankData === 'object') ? tankData.max_gallons : null;
            let availableCapacity = (tankData && typeof tankData === 'object') ? tankData.available_capacity : null;

            if (availableCapacity === null && currentGallons !== null && currentGallons !== undefined && maxGallons !== null && maxGallons !== undefined) {
                availableCapacity = Number(currentGallons) - Number(maxGallons);
            }

            const valueEl = card.querySelector('[data-role="tank-gallons"]');
            if (valueEl) valueEl.textContent = this.formatNumber(currentGallons, 0);

            const capacityEl = card.querySelector('[data-role="tank-capacity"]');
            if (capacityEl) capacityEl.textContent = this.formatNumber(maxGallons, 0);

            const availableEl = card.querySelector('[data-role="tank-available"]');
            if (availableEl) {
                availableEl.textContent = this.formatNumber(availableCapacity, 0);
                const overCapacity = availableCapacity !== null
                    && availableCapacity !== undefined
                    && !Number.isNaN(Number(availableCapacity))
                    && Number(availableCapacity) > 0;
                availableEl.classList.toggle('text-danger', overCapacity);
            }

            // Optional projection: tank gallons after scheduled desk usage
            const normalizedLookupKey = (tankName || '').replace(/\s+/g, '').toUpperCase();
            const linkedComponentCode = tankComponentMap[normalizedLookupKey];
            const projectionEl = card.querySelector('[data-role="tank-after-scheduled"]');
            if (projectionEl && linkedComponentCode) {
                const scheduledUsage = this.getScheduledUsageForComponent(linkedComponentCode);
                let projectedGallons = null;
                if (scheduledUsage !== null && currentGallons !== null && currentGallons !== undefined) {
                    projectedGallons = Number(currentGallons) - Number(scheduledUsage);
                }

                projectionEl.textContent = this.formatNumber(projectedGallons, 0);
                projectionEl.classList.toggle('text-danger', this.isNegative(projectedGallons));
            }
        });
    }

    formatNumber(value, decimals = 1) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '—';
        }
        const formatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
        return formatter.format(Number(value));
    }

    formatDate(value) {
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return '—';
        return parsed.toLocaleDateString();
    }

    formatProjectedDatetime(isoString) {
        const dt = new Date(isoString);
        if (Number.isNaN(dt.getTime())) return null;
        const formatted = dt.toLocaleString(undefined, {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
        return formatted;
    }

    async getProjectedDatetime(hours, startDatetime) {
        const numericHours = Number(hours);
        if (Number.isNaN(numericHours)) return null;

        const cacheKey = `${numericHours}__${startDatetime || 'none'}`;

        if (this.projectedDatetimeCache.has(cacheKey)) {
            return this.projectedDatetimeCache.get(cacheKey);
        }

        const params = new URLSearchParams({ production_hours: numericHours });
        if (startDatetime) params.set('start_datetime', startDatetime);
        const fetchPromise = fetch(`/core/api/projected-production-datetime/?${params.toString()}`, {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
            },
        })
            .then(response => (response.ok ? response.json() : null))
            .then(data => {
                if (!data || !data.projected_datetime) return null;
                return this.formatProjectedDatetime(data.projected_datetime);
            })
            .catch(() => null);

        this.projectedDatetimeCache.set(cacheKey, fetchPromise);
        return fetchPromise;
    }

    isNegative(value) {
        if (value === null || value === undefined) return false;
        return Number(value) < 0;
    }
}


export class ProductionHolidaysPage {
    constructor() {
        this.table = document.getElementById('production-holidays-table');
        this.tbody = this.table ? this.table.querySelector('tbody') : null;
        this.addButton = document.getElementById('add-holiday-btn');
        this.csrfToken = this.getCsrfToken();
        this.apiBase = '/core/api/production-holiday/';
        this.activeRow = null;

        if (this.table) {
            this.init();
        }
    }

    init() {
        this.table.querySelectorAll('.filterableRow').forEach((row) => this.attachRowEvents(row));
        if (this.addButton) {
            this.addButton.addEventListener('click', () => this.handleAdd());
        }
    }

    getCsrfToken() {
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput && csrfInput.value) return csrfInput.value;
        const value = `; ${document.cookie}`;
        const parts = value.split('; csrftoken=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    attachRowEvents(row) {
        const editBtn = row.querySelector('.edit-row-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.enterEditMode(row));
        }
    }

    getRowSnapshot(row) {
        const data = {};
        row.querySelectorAll('[data-field]').forEach((cell) => {
            const field = cell.dataset.field;
            if (field === 'actions') return;
            if (field === 'active') {
                const badge = cell.querySelector('.badge');
                data[field] = badge ? badge.textContent.trim().toLowerCase() === 'yes' : false;
                return;
            }
            data[field] = (cell.textContent || '').trim();
        });
        return data;
    }

    buildInput(field, value) {
        if (field === 'date') {
            const input = document.createElement('input');
            input.type = 'date';
            input.className = 'form-control form-control-sm';
            input.value = value || '';
            input.dataset.field = field;
            input.dataset.isInput = 'true';
            return input;
        }
        if (field === 'active') {
            const wrapper = document.createElement('div');
            wrapper.className = 'form-check d-flex justify-content-center m-0';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input';
            checkbox.checked = Boolean(value);
            checkbox.dataset.field = field;
            checkbox.dataset.isInput = 'true';
            wrapper.appendChild(checkbox);
            return wrapper;
        }
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control form-control-sm';
        input.value = value || '';
        input.dataset.field = field;
        input.dataset.isInput = 'true';
        return input;
    }

    renderDisplay(field, value) {
        if (field === 'active') {
            return value ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>';
        }
        return value ? this.escapeHtml(value) : '';
    }

    escapeHtml(value = '') {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        const stringValue = value == null ? '' : String(value);
        return stringValue.replace(/[&<>"']/g, (char) => map[char]);
    }

    enterEditMode(row) {
        if (this.activeRow && this.activeRow !== row) {
            const currentData = this.getRowSnapshot(this.activeRow);
            const abandon = window.confirm('You have unsaved changes. Abandon them?');
            if (!abandon) return;
            if (this.activeRow.dataset.isNew === 'true') {
                this.activeRow.remove();
            } else {
                this.exitEditMode(this.activeRow, JSON.stringify(currentData));
            }
            this.activeRow = null;
        }

        if (this.activeRow === row) return;

        const snapshot = this.getRowSnapshot(row);
        row.dataset.snapshot = JSON.stringify(snapshot);
        row.classList.add('table-warning');

        row.querySelectorAll('[data-field]').forEach((cell) => {
            const field = cell.dataset.field;
            if (field === 'actions') {
                cell.innerHTML = '';
                const group = document.createElement('div');
                group.className = 'btn-group btn-group-sm';
                const saveBtn = document.createElement('button');
                saveBtn.type = 'button';
                saveBtn.className = 'btn btn-success save-row-btn';
                saveBtn.innerHTML = '<i class="fas fa-check"></i>';
                const cancelBtn = document.createElement('button');
                cancelBtn.type = 'button';
                cancelBtn.className = 'btn btn-outline-secondary cancel-row-btn';
                cancelBtn.innerHTML = '<i class="fas fa-times"></i>';
                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.className = 'btn btn-outline-danger delete-row-btn';
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                group.append(saveBtn, cancelBtn, deleteBtn);
                cell.appendChild(group);
                saveBtn.addEventListener('click', () => this.handleSave(row));
                cancelBtn.addEventListener('click', () => {
                    if (row.dataset.isNew === 'true') {
                        row.remove();
                        this.activeRow = null;
                        return;
                    }
                    this.exitEditMode(row, row.dataset.snapshot);
                });
                deleteBtn.addEventListener('click', () => this.handleDelete(row));
                return;
            }
            const value = snapshot[field];
            const input = this.buildInput(field, value);
            cell.innerHTML = '';
            cell.appendChild(input);
        });

        this.activeRow = row;
        const firstInput = row.querySelector('[data-is-input="true"]');
        if (firstInput) firstInput.focus();
    }

    exitEditMode(row, snapshotJSON) {
        const snapshot = snapshotJSON ? JSON.parse(snapshotJSON) : this.getRowSnapshot(row);
        row.querySelectorAll('[data-field]').forEach((cell) => {
            const field = cell.dataset.field;
            if (field === 'actions') {
                cell.innerHTML = '<button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit"><i class="fas fa-edit"></i></button>';
                this.attachRowEvents(row);
                return;
            }
            const value = snapshot[field];
            cell.innerHTML = this.renderDisplay(field, value);
        });

        row.classList.remove('table-warning');
        delete row.dataset.snapshot;
        delete row.dataset.isNew;
        this.activeRow = null;
    }

    async handleSave(row) {
        const isNew = row.dataset.isNew === 'true';
        const holidayId = row.dataset.holidayId;
        const originalSnapshot = row.dataset.snapshot ? JSON.parse(row.dataset.snapshot) : {};
        const payload = {};

        row.querySelectorAll('[data-field]').forEach((cell) => {
            const field = cell.dataset.field;
            if (field === 'actions') return;
            const input = cell.querySelector('[data-is-input="true"]');
            if (!input) return;
            let value;
            if (input.type === 'checkbox') {
                value = input.checked;
            } else {
                value = input.value.trim();
            }
            const originalValue = originalSnapshot[field];
            if (isNew || value !== originalValue) {
                payload[field] = value;
            }
        });

        if (!payload.date) {
            alert('Date is required.');
            return;
        }

        const buttons = row.querySelectorAll('.save-row-btn, .cancel-row-btn, .delete-row-btn');
        buttons.forEach((btn) => { if (btn) btn.disabled = true; });
        const saveBtn = row.querySelector('.save-row-btn');
        const originalSaveHtml = saveBtn ? saveBtn.innerHTML : '';
        if (saveBtn) {
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        }

        try {
            let response;
            if (isNew) {
                response = await this.createHoliday(payload);
                row.dataset.holidayId = response.holiday.id;
            } else {
                response = await this.updateHoliday(holidayId, payload);
            }
            const snapshot = {
                date: response.holiday.date,
                description: response.holiday.description,
                active: response.holiday.active,
            };
            this.exitEditMode(row, JSON.stringify(snapshot));
        } catch (error) {
            console.error(error);
            alert(error.message || 'Unable to save holiday.');
            buttons.forEach((btn) => { if (btn) btn.disabled = false; });
            if (saveBtn) saveBtn.innerHTML = originalSaveHtml;
            return;
        }

        buttons.forEach((btn) => { if (btn) btn.disabled = false; });
        if (saveBtn) saveBtn.innerHTML = originalSaveHtml;
    }

    async createHoliday(payload) {
        const response = await fetch(`${this.apiBase}create/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(payload),
        });

        let data;
        try {
            data = await response.json();
        } catch (error) {
            throw new Error('Unexpected response from the server.');
        }

        if (!response.ok || data.status !== 'success') {
            const message = data.error || 'Unable to create holiday.';
            throw new Error(message);
        }
        return data;
    }

    async updateHoliday(id, payload) {
        const response = await fetch(`${this.apiBase}${id}/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(payload),
        });

        let data;
        try {
            data = await response.json();
        } catch (error) {
            throw new Error('Unexpected response from the server.');
        }

        if (!response.ok || data.status !== 'success') {
            const message = data.error || 'Unable to update holiday.';
            throw new Error(message);
        }
        return data;
    }

    async handleDelete(row) {
        if (row.dataset.isNew === 'true') {
            row.remove();
            if (this.activeRow === row) this.activeRow = null;
            return;
        }
        const holidayId = row.dataset.holidayId;
        if (!holidayId) return;

        const dateText = (row.querySelector('[data-field="date"]')?.textContent || '').trim();
        const confirmDelete = window.confirm(`Delete holiday ${dateText || holidayId}? This cannot be undone.`);
        if (!confirmDelete) return;

        const buttons = row.querySelectorAll('.save-row-btn, .cancel-row-btn, .delete-row-btn');
        buttons.forEach((btn) => { if (btn) btn.disabled = true; });

        try {
            const response = await fetch(`${this.apiBase}${holidayId}/delete/`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({}),
            });
            let data;
            try {
                data = await response.json();
            } catch (error) {
                throw new Error('Unexpected response from the server.');
            }
            if (!response.ok || data.status !== 'success') {
                const message = data.error || 'Unable to delete holiday.';
                throw new Error(message);
            }
            row.remove();
            if (this.activeRow === row) this.activeRow = null;
        } catch (error) {
            console.error(error);
            alert(error.message || 'Unable to delete holiday.');
            buttons.forEach((btn) => { if (btn) btn.disabled = false; });
            return;
        }

        buttons.forEach((btn) => { if (btn) btn.disabled = false; });
    }

    buildRow(holiday) {
        const row = document.createElement('tr');
        row.className = 'filterableRow';
        if (holiday.id != null) {
            row.dataset.holidayId = holiday.id;
        }
        if (holiday.isNew) {
            row.dataset.isNew = 'true';
        }
        row.innerHTML = `
            <td data-field="date">${this.escapeHtml(holiday.date || '')}</td>
            <td data-field="description" class="text-break">${this.escapeHtml(holiday.description || '')}</td>
            <td data-field="active" class="text-center">${this.renderDisplay('active', holiday.active)}</td>
            <td data-field="actions" class="text-center">
                <button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
        `;
        return row;
    }

    async handleAdd() {
        if (!this.tbody) return;

        if (this.activeRow) {
            const currentData = this.getRowSnapshot(this.activeRow);
            const abandon = window.confirm('You have unsaved changes. Abandon them?');
            if (!abandon) return;
            if (this.activeRow.dataset.isNew === 'true') {
                this.activeRow.remove();
                this.activeRow = null;
            } else {
                this.exitEditMode(this.activeRow, JSON.stringify(currentData));
            }
        }

        const template = {
            id: null,
            date: '',
            description: '',
            active: true,
            isNew: true,
        };
        const row = this.buildRow(template);
        this.tbody.prepend(row);
        this.attachRowEvents(row);
        this.enterEditMode(row);
    }
}
