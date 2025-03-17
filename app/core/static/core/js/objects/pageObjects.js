import { getMaxProducibleQuantity, getBlendSheet, getBlendSheetTemplate, getURLParameter, getNewBlendInstructionInfo, getBlendCrewInitials, getItemInfo } from '../requestFunctions/requestFunctions.js'
import { getContainersFromCount } from '../requestFunctions/requestFunctions.js'
import { updateBlendInstructionsOrder, logContainerLabelPrint, updateCountCollection } from '../requestFunctions/updateFunctions.js'
import { ItemReferenceFieldPair } from './lookupFormObjects.js'


export function calculateVarianceAndCount(countRecordId){
    const quantityInputs = $(`input.form-control.container_quantity[data-countrecord-id="${countRecordId}"]`);
    let totalQuantity = 0;
    quantityInputs.each(function() {
        let value = parseFloat($(this).val()) || 0;
        let recordType = getURLParameter('recordType');
        let tareWeight = 0;
        if (recordType === 'blendcomponent') {
            tareWeight = parseFloat($(this).closest('tr').find('input.tare_weight').val()) || 0;
        }
        value = value - tareWeight;
        totalQuantity += value;
    });
    $(`input.counted_quantity[data-countrecord-id="${countRecordId}"]`).val(totalQuantity);
    const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text());
    const variance = totalQuantity - expectedQuantity;
    $(`td.tbl-cell-variance[data-countrecord-id="${countRecordId}"]`).text(variance.toFixed(4));
};

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
        const tareWeightInput = row.find('.tare_weight input');
        
        if (checkboxElement.is(':checked')) {
            tareWeightInput.prop('disabled', true);
            tareWeightInput.val('');
        } else {
            tareWeightInput.prop('disabled', false);
            
            // Check if tare weight is empty or zero, and if so, set it based on container type
            const tareValue = parseFloat(tareWeightInput.val()) || 0;
            if (tareValue === 0) {
                // Get the container manager if available
                let containerManager = null;
                try {
                    containerManager = window.countListPage && window.countListPage.containerManager;
                } catch(e) {
                    // No container manager available
                }
                
                if (containerManager) {
                    const containerType = row.find('select.container_type').val();
                    const recordType = getURLParameter('recordType');
                    const tareWeight = containerManager._getTareWeightForContainerType(containerType, recordType);
                    tareWeightInput.val(tareWeight);
        } else {
                    // Fallback to using updateTareWeight function
                    const containerType = row.find('select.container_type');
                    if (containerType.length) {
                        updateTareWeight(containerType, row.attr('data-container-id'));
                    }
                }
            }
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
            return this.cachedContainers.get(countRecordId);
        }
        
        // Get from server
        const containers = getContainersFromCount(countRecordId, recordType);
        this.cachedContainers.set(countRecordId, containers);
        return containers;
    }
    
    /**
     * Renders container rows for a specific count record
     * @param {string|number} countRecordId - The ID of the count record
     * @param {string} recordType - The type of record (blend, blendcomponent, etc.)
     * @param {jQuery} containerTableBody - The container table body element
     * @returns {string} - The HTML for the container rows
     */
    renderContainerRows(countRecordId, recordType, containerTableBody) {
        const containers = this.getContainers(countRecordId, recordType);
            let tableRows = '';
        
        // If no containers exist, create a default empty container row
        if (containers.length === 0) {
            tableRows = this._createEmptyContainerRow(countRecordId, recordType);
            } else {
            // Create a row for each container
            containers.forEach(container => {
                tableRows += this._createContainerRow(container, countRecordId, recordType);
            });
        }
        
        // Clear and populate the container table
        if (containerTableBody.find('tbody').length) {
            containerTableBody.find('tbody').empty().append(tableRows);
        } else {
            containerTableBody.empty().append(tableRows);
        }
        
        // Initialize checkbox states
        initializeNetMeasurementCheckboxes(containerTableBody);
        
        // Set up event handlers
        this._setupEventHandlers(containerTableBody, countRecordId, recordType);
        
        return tableRows;
    }
    
    /**
     * Creates HTML for an empty container row
     * @private
     */
    _createEmptyContainerRow(countRecordId, recordType) {
        // Determine the default container type and its associated tare weight
        const defaultContainerType = "275gal tote";
        const defaultTareWeight = this._getTareWeightForContainerType(defaultContainerType, recordType);
        
        return `<tr data-container-id="0" data-countrecord-id="${countRecordId}" class="containerRow">
                    <td class='container_id' style="display:none;">
                        <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="0" data-container-id="0">
                    </td>
                    <td class='quantity'><input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="" data-container-id="0"></td>
                    <td class='container_type'>
                        <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="0">
                    <option value="275gal tote" selected data-countrecord-id="${countRecordId}">275gal Tote</option>
                            <option value="poly drum" data-countrecord-id="${countRecordId}">Poly Drum</option>
                            <option value="regular metal drum" data-countrecord-id="${countRecordId}">Regular Metal Drum</option>
                            <option value="large poly tote" data-countrecord-id="${countRecordId}">Large Poly Tote</option>
                            <option value="stainless steel tote" data-countrecord-id="${countRecordId}">Stainless Steel Tote</option>
                            <option value="300gal tote" data-countrecord-id="${countRecordId}">300gal Tote</option>
                            <option value="small poly drum" data-countrecord-id="${countRecordId}">Small Poly Drum</option>
                            <option value="enzyme metal drum" data-countrecord-id="${countRecordId}">Enzyme Metal Drum</option>
                            <option value="plastic pail" data-countrecord-id="${countRecordId}">Plastic Pail</option>
                            <option value="metal dye_frag pail" data-countrecord-id="${countRecordId}">Metal Dye/Frag Pail</option>
                            <option value="cardboard box" data-countrecord-id="${countRecordId}">Cardboard Box</option>
                            <option value="gallon jug" data-countrecord-id="${countRecordId}">Gallon Jug</option>
                            <option value="storage tank" data-countrecord-id="${countRecordId}">Storage Tank</option>
                        </select>
                    </td>
                    <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
                <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="${defaultTareWeight}" data-container-id="0">
                    </td>
                    <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                <input type="checkbox" class="container_net_measurement" data-countrecord-id="${countRecordId}" data-container-id="0">
                    </td>
                    <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="0"></i></td>
        </tr>`;
    }
    
    /**
     * Creates HTML for a container row with data
     * @private
     */
    _createContainerRow(container, countRecordId, recordType) {
        return `<tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
                        <td class='container_id' style="display:none;">
                            <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="${container.container_id}" data-container-id="${container.container_id}">
                        </td>
                        <td class='quantity'>
                            <input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="${container.container_quantity || ''}" data-container-id="${container.container_id}">
                        </td>
                        <td class='container_type'>
                            <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
                            <option value="275gal tote" ${container.container_type === '275gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">275gal tote</option>
                            <option value="poly drum" ${container.container_type === 'poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Poly Drum</option>
                            <option value="regular metal drum" ${container.container_type === 'regular metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Regular Metal Drum</option>
                            <option value="large poly tote" ${container.container_type === 'large poly tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Large Poly Tote</option>
                            <option value="stainless steel tote" ${container.container_type === 'stainless steel tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Stainless Steel Tote</option>
                            <option value="300gal tote" ${container.container_type === '300gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">300gal Tote</option>
                            <option value="small poly drum" ${container.container_type === 'small poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Small Poly Drum</option>
                            <option value="enzyme metal drum" ${container.container_type === 'enzyme metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Enzyme Metal Drum</option>
                            <option value="plastic pail" ${container.container_type === 'plastic pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Plastic Pail</option>
                            <option value="metal dye_frag pail" ${container.container_type === 'metal dye_frag pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Metal Dye/Frag Pail</option>
                            <option value="cardboard box" ${container.container_type === 'cardboard box' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Cardboard Box</option>
                            <option value="gallon jug" ${container.container_type === 'gallon jug' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Gallon Jug</option>
                            <option value="storage tank" ${container.container_type === 'storage tank' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Storage Tank</option>
                            </select>
                        </td>
                        <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
                            <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="${container.tare_weight || ''}" data-container-id="${container.container_id}">
                        </td>
                        <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                <input type="checkbox" class="container_net_measurement" ${container.net_measurement === true || container.net_measurement === "true" ? 'checked' : ''} data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
                        </td>
                        <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i></td>
        </tr>`;
    }
    
    /**
     * Sets up event handlers for a container table
     * @private
     */
    _setupEventHandlers(containerTableBody, countRecordId, recordType) {
        const self = this; // Store reference to ContainerManager for event callbacks
        
        // Container type change handler
        $(containerTableBody).find('select.container_type').off('change').on('change', function() {
            const containerId = $(this).attr('data-container-id');
            console.log(`Container type changed for container ${containerId}`);
            
            // Update tare weight based on container type
            updateTareWeight($(this), containerId);
            
            // Send update to server
            self._sendUpdateToServer(countRecordId, containerId, 'update');
            
            // Recalculate variance
            calculateVarianceAndCount(countRecordId);
        });
        
        // Container quantity change handler
        $(containerTableBody).find('input.container_quantity').off('input').on('input', function() {
            const $this = $(this);
            const containerId = $this.attr('data-container-id');
            
            // Clear any pending updates
            clearTimeout($this.data('debounce-timer'));
            
            // Provide immediate visual feedback to the user
            $this.css('background-color', '#FFFACD'); // Subtle yellow to indicate pending change
            
            // Schedule the expensive operations with debounce
            $this.data('debounce-timer', setTimeout(function() {
                console.log(`Debounced quantity change for container ${containerId} after 500ms`);
                
                // Restore original background
                $this.css('background-color', '');
                
                // Perform expensive operations
                calculateVarianceAndCount(countRecordId);
                self._sendUpdateToServer(countRecordId, containerId, 'update');
            }, 400)); // 400ms debounce delay
        });
        
        // Tare weight input handler
        $(containerTableBody).find('input.tare_weight').off('input').on('input', function() {
            console.log(`Tare weight changed`);
            self._handleTareWeightChange($(this), countRecordId);
        });
        
        // Net measurement checkbox handler
        $(containerTableBody).find('input.container_net_measurement').off('change').on('change', function() {
            console.log(`Net measurement checkbox changed`);
            self._handleTareCheckedChange($(this), countRecordId);
        });
        
        // Delete container row handler
        $(containerTableBody).find('.fa.fa-trash.row-clear').off('click').on('click', function() {
                const containerId = $(this).attr('data-container-id');
            console.log(`Deleting container ${containerId}`);
            
            // Remove the row from the DOM
            $(this).closest('tr').remove();
            
            // Send delete event to server
            self._sendUpdateToServer(countRecordId, containerId, 'delete');
            
            // Recalculate variance
            calculateVarianceAndCount(countRecordId);
        });
        
        // Add container row handler - IMPORTANT: We need to find this button outside the table body
        const addButtonSelector = `.add-container-row[data-countrecord-id="${countRecordId}"]`;
        
        // Find the add button by its data attribute that matches this countRecordId
        $(addButtonSelector).off('click').on('click', function() {
            console.log(`Add container row button clicked for record ${countRecordId}`);
            self._handleAddContainerRow($(this), countRecordId, recordType);
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
        console.log(`🔮 Adding container row for count record ${countRecordId}`, buttonElement);
        
        // Ensure we have the correct record ID
        const recordId = buttonElement.attr('data-countrecord-id') || countRecordId;
        if (!recordId) {
            console.error("Cannot add container row: Missing record ID");
            return;
        }
        
        // Find the container table for this record
        const containerTable = $(`table.container-table[data-countrecord-id="${recordId}"]`);
        if (containerTable.length === 0) {
            console.error(`Cannot find container table for record ID ${recordId}`);
            return;
        }
        
        // Find the container table body
        const containerTableBody = containerTable.find('tbody.containerTbody');
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
        
        // Update the delete button with the new container ID
        newRow.find('.fa.fa-trash.row-clear').attr('data-container-id', newContainerId);
        
        // Set the appropriate tare weight based on the selected container type
        const selectedContainerType = newRow.find('select.container_type').val();
        const tareWeight = this._getTareWeightForContainerType(selectedContainerType, recordType);
        
        // Update the tare weight input
        newRow.find('input.tare_weight').val(tareWeight);
        
        if (tareWeight > 0) {
            console.log(`🧪 Set initial tare weight to ${tareWeight} for container type ${selectedContainerType}`);
        }
        
        // Setup event handlers for the new row
        
        // Container type change handler
        newRow.find('select.container_type').off('change').on('change', function() {
            console.log(`Container type changed for container ${newContainerId}`);
            updateTareWeight($(this), newContainerId);
            self._sendUpdateToServer(recordId, newContainerId, 'update');
                calculateVarianceAndCount(recordId);
        });
        
        // Container quantity change handler
        newRow.find('input.container_quantity').off('input').on('input', function() {
            console.log(`Container quantity changed for container ${newContainerId}`);
            calculateVarianceAndCount(recordId);
            self._sendUpdateToServer(recordId, newContainerId, 'update');
        });
        
        // Tare weight input handler
        newRow.find('input.tare_weight').off('input').on('input', function() {
            console.log(`Tare weight changed for container ${newContainerId}`);
            self._handleTareWeightChange($(this), recordId);
        });
        
        // Net measurement checkbox handler
        newRow.find('input.container_net_measurement').off('change').on('change', function() {
            console.log(`Net measurement checkbox changed for container ${newContainerId}`);
            self._handleTareCheckedChange($(this), recordId);
        });
        
        // Delete container row handler
        newRow.find('.fa.fa-trash.row-clear').off('click').on('click', function() {
            console.log(`Deleting container ${newContainerId}`);
            $(this).closest('tr').remove();
            self._sendUpdateToServer(recordId, newContainerId, 'delete');
            calculateVarianceAndCount(recordId);
        });
        
        // Append the new row to the container table body
        containerTableBody.append(newRow);
        
        // Initialize checkbox relationships for this new row
        initializeNetMeasurementCheckboxes(newRow);
        
        // Send update to server with new container ID
        this._sendUpdateToServer(recordId, newContainerId, 'add');
        
        console.log(`✨ Successfully added new container row with ID ${newContainerId}`);
        
        // Return focus to the quantity field in the new row
        newRow.find('input.container_quantity').focus();
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
            console.log("🔌 Updated WebSocket reference in ContainerManager");
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
            const countRecordId = $(this).attr('data-countrecord-id');
            const recordType = getURLParameter('recordType');
            $(this).off('click').on('click', function() {
                console.log("Global add container row handler clicked for record", countRecordId);
                self._handleAddContainerRow($(this), countRecordId, recordType);
            });
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
            const containerId = parseInt($(this).attr('data-container-id')) || 0;
            if (containerId > highestId) {
                highestId = containerId;
            }
        });
        
        // Return the next available ID
        return highestId + 1;
    }
    
    /**
     * Sends an update to the server via WebSocket
     * @param {string} recordId - The ID of the count record
     * @param {number} containerId - The ID of the container
     * @param {string} action - The action being performed (add, update, delete)
     * @private
     */
    _sendUpdateToServer(recordId, containerId, action) {
        try {
            console.log(`📡 Sending ${action} container update to server for container ${containerId} in record ${recordId}`);
            
            // Gather all container data for this record
            const containers = this._gatherContainerData(recordId);
            
            // Get other record data
            const recordData = {
                'counted_quantity': $(`input[data-countrecord-id="${recordId}"].counted_quantity`).val(),
                'expected_quantity': $(`span[data-countrecord-id="${recordId}"].expected-quantity-span`).text().trim(),
                'variance': $(`td[data-countrecord-id="${recordId}"].tbl-cell-variance`).text(),
                'counted_date': $(`td[data-countrecord-id="${recordId}"].tbl-cell-counted_date`).text(),
                'counted': $(`input[data-countrecord-id="${recordId}"].counted-input`).prop("checked"),
                'comment': $(`textarea[data-countrecord-id="${recordId}"].comment`).val() || '',
                'location': $(`select[data-countrecord-id="${recordId}"].location-selector`).val(),
                'containers': containers,
                'containerId': containerId,
                'record_type': getURLParameter("recordType")
            };
            
            // Call the original sendCountRecordChange function with our gathered data
            // This maintains backward compatibility with the existing WebSocket handling
            const eventTarget = $(`[data-countrecord-id="${recordId}"]`).first();
            sendCountRecordChange(eventTarget, this.webSocket, containerId);
            
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
        
        return containers;
    }

    /**
     * Handles changes to tare weight fields
     * @param {jQuery} inputElement - The input element that was changed
     * @param {string} recordId - The ID of the count record
     * @private
     */
    _handleTareWeightChange(inputElement, recordId) {
        // Get the container ID from the parent row
        const containerId = inputElement.closest('tr').attr('data-container-id');
        
        // Calculate variance and update count
        calculateVarianceAndCount(recordId);
        
        // Send update to server
        this._sendUpdateToServer(recordId, containerId, 'update');
    }
    
    /**
     * Handles changes to gross weight fields
     * @param {jQuery} inputElement - The input element that was changed
     * @param {string} recordId - The ID of the count record
     * @private
     */
    _handleGrossWeightChange(inputElement, recordId) {
        // Get the container ID from the parent row
        const containerId = inputElement.closest('tr').attr('data-container-id');
        
        // Calculate variance and update count
        calculateVarianceAndCount(recordId);
        
        // Send update to server
        this._sendUpdateToServer(recordId, containerId, 'update');
    }
    
    /**
     * Handles changes to net weight fields
     * @param {jQuery} inputElement - The input element that was changed
     * @param {string} recordId - The ID of the count record
     * @private
     */
    _handleNetWeightChange(inputElement, recordId) {
        // Get the container ID from the parent row
        const containerId = inputElement.closest('tr').attr('data-container-id');
        
        // Calculate variance and update count
        calculateVarianceAndCount(recordId);
        
        // Send update to server
        this._sendUpdateToServer(recordId, containerId, 'update');
    }
    
    /**
     * Handles changes to tare weight checkbox fields
     * @param {jQuery} inputElement - The checkbox that was changed
     * @param {string} recordId - The ID of the count record
     * @private
     */
    _handleTareCheckedChange(inputElement, recordId) {
        // Get the container ID from the parent row
        const containerId = inputElement.closest('tr').attr('data-container-id');
        const row = inputElement.closest('tr');
        
        // Find tare weight input in the same row
        const tareWeightInput = row.find('input.tare_weight');
        
        // If checked, disable tare weight field and clear its value
        if (inputElement.is(':checked')) {
            tareWeightInput.prop('disabled', true);
            tareWeightInput.val('');
        } else {
            // Re-enable the tare weight field
            tareWeightInput.prop('disabled', false);
            
            // Get the selected container type and record type
            const containerType = row.find('select.container_type').val();
            const recordType = getURLParameter('recordType');
            
            // Set the appropriate tare weight based on container type
            const tareWeight = this._getTareWeightForContainerType(containerType, recordType);
            tareWeightInput.val(tareWeight);
            
            console.log(`🔄 Restored tare weight to ${tareWeight} for container type ${containerType}`);
        }
        
        // Calculate variance and update count
        calculateVarianceAndCount(recordId);
        
        // Send update to server
        this._sendUpdateToServer(recordId, containerId, 'update');
    }

    /**
     * Gets the appropriate tare weight based on container type and record type
     * @param {string} containerType - The type of container
     * @param {string} recordType - The type of record (blend, blendcomponent, etc.)
     * @returns {number} - The tare weight value
     * @private
     */
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
            "metal dye_frag pail": 4,
            "cardboard box": 2,
            "gallon jug": 1,
            "large poly tote": 0,
            "stainless steel tote": 0,
            "storage tank": 0
        };
        
        // Return the tare weight for the container type, or 0 if not found
        return tareWeightMap[containerType] || 0;
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
    let containers = [];
    const thisContainerTable = $(`table[data-countrecord-id="${dataCountRecordId}"].container-table`);

    thisContainerTable.find('tr.containerRow').each(function() {
        let containerData = {
            'container_id': $(this).find(`input.container_id`).val(),
            'container_quantity': $(this).find(`input.container_quantity`).val(),
            'container_type': $(this).find(`select.container_type`).val(),
            'tare_weight': $(this).find(`input.tare_weight`).val(),
            'net_measurement': $(this).find(`input.container_net_measurement`).is(':checked'),
        };
        containers.push(containerData);
    });

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
        'containers': containers,
        'containerId': containerId,
        'record_type': recordType
    }
    // console.log(`sending ${recordData['containers']}`);

    thisCountListWebSocket.updateCount(recordId, recordType, recordData);
};

export function updateCheckBoxCellColors() {
    const countedCells = $('.tbl-cell-counted');
    countedCells.each(function() {
        const checkbox = $(this).find('input[type="checkbox"]');
        if (checkbox.is(':checked')) {
            $(this).removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
        } else {
            $(this).removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
        }
    });
}

export function updateTareWeight(eventTarget, containerId) {
    let recordType = getURLParameter('recordType');
    
    // Get the closest container manager instance (if available in page)
    let containerManager = null;
    try {
        containerManager = window.countListPage && window.countListPage.containerManager;
    } catch(e) {
        // No container manager available, use legacy approach
    }
    
    const containerType = eventTarget.val();
    let tareWeight = 0;
    
    if (containerManager) {
        // Use the container manager's helper function if available
        tareWeight = containerManager._getTareWeightForContainerType(containerType, recordType);
    } else {
        // Legacy approach
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
            else if (containerType === "metal dye_frag pail") tareWeight = 4;
            else if (containerType === "cardboard box") tareWeight = 2;
            else if (containerType === "gallon jug") tareWeight = 1;
            else if (containerType === "storage tank") tareWeight = 0;
        }
    }
    
    // Set the tare weight
    const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
    tareWeightInput.val(tareWeight);
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
        console.log(`🧪 Creating new count record row for ID ${recordId} using template`, data);
        
        // Get the record type from URL parameter or options
        const recordType = options.recordType || getURLParameter('recordType');
        
        // Get the location options from existing selector if available
        const existingSelector = document.querySelector('select.location-selector');
        const locationOptions = existingSelector ? 
            Array.from(existingSelector.options).map(opt => ({ 
                value: opt.value, 
                text: opt.text,
                selected: opt.value === data.location
            })) : 
            [{ value: data.location || '', text: data.location || '', selected: true }];
        
        // Create location options HTML
        const locationOptionsHtml = locationOptions.map(opt => 
            `<option value="${opt.value}" ${opt.selected ? 'selected' : ''}>${opt.text}</option>`
        ).join('');
        
        // Create the row HTML from scratch using a template string
        const rowHtml = `
            <tr data-countrecord-id="${recordId}" class="countRow">
                <td data-countrecord-id="${recordId}" class="tbl-cell-item_code text-right">
                    <div class="dropdown">
                        <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown" readonly="readonly">${data.item_code}</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item partialContainerLabelLink" data-itemcode="${data.item_code}">Partial Container Label</a></li>
                        </ul>
                    </div>
                </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-item_description">${data.item_description}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-expected_quantity">
                    <span data-countrecord-id="${recordId}" class="expected-quantity-span">${parseFloat(data.expected_quantity).toFixed(4)}</span> <em>${data.standard_uom || ''}</em>
                    <span></span> <i class="fa fa-refresh qtyrefreshbutton" itemcode="${data.item_code}" data-countrecord-id="${recordId}" aria-hidden="true"></i>
                </td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-containers">
                    <button class="containers" data-countrecord-id="${recordId}" data-bs-toggle="modal" data-bs-target="#containersModal${recordId}">Enter ></button>
                    <div class="modal fade" id="containersModal${recordId}" tabindex="-1" aria-labelledby="containersModalLabel${recordId}" aria-hidden="true">
                        <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button hidden=true class="btn btn-secondary multi-container-print-button" data-countrecord-id="${recordId}">
                                    <i class="fa fa-print" aria-hidden="true"></i>
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
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted_date noPrint" readonly>${data.counted_date}</td>
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
                    <i class="fa fa-trash discardButton" data-countrecord-id="${recordId}" data-countlist-id="${options.listId || document.querySelector('#countsTable').getAttribute('data-countlist-id')}" aria-hidden="true"></i>
                </td>
            </tr>
        `;
        
        // Create a DOM element from the HTML
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = rowHtml.trim();
        const newRow = tempContainer.firstChild;
        
        // DEBUG: Check if the row was created properly
        if (!newRow || !newRow.tagName || newRow.tagName.toLowerCase() !== 'tr') {
            console.error('🔥 Failed to create TR element from template!', { 
                created: newRow, 
                html: rowHtml.substring(0, 100) + '...' 
            });
            
            // Emergency fallback - create the row manually
            const emergencyRow = document.createElement('tr');
            emergencyRow.setAttribute('data-countrecord-id', recordId);
            emergencyRow.className = 'countRow emergency-template-row';
            emergencyRow.style.backgroundColor = '#ffccff';
            
            // Add a simple cell with the item code
            const tdCode = document.createElement('td');
            tdCode.textContent = data.item_code;
            emergencyRow.appendChild(tdCode);
            
            // Add a simple cell with the item description
            const tdDesc = document.createElement('td');
            tdDesc.textContent = data.item_description;
            emergencyRow.appendChild(tdDesc);
            
            console.warn('🚑 Using emergency fallback row!');
            return emergencyRow;
        }
        
        // Ensure all data-countrecord-id attributes are set
        Array.from(newRow.querySelectorAll('*[data-countrecord-id]')).forEach(el => {
            if (el.getAttribute('data-countrecord-id') !== recordId.toString()) {
                console.warn(`Fixed incorrect data-countrecord-id on element`, el);
                el.setAttribute('data-countrecord-id', recordId);
            }
        });
        
        // Double-check modal bindings to prevent conflicts
        this._verifyModalBindings(newRow, recordId);
        
        return newRow;
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
            
            // 2. Get the current modal ID and verify it contains the recordId
            const currentModalId = modal.id;
            if (!currentModalId || !currentModalId.includes(recordId)) {
                console.warn(`⚠️ Modal ID needs correction: ${currentModalId} → containersModal${recordId}`);
                
                // Generate a unique ID based on recordId and timestamp
                const newModalId = `containersModal${recordId}_${Date.now()}`;
                modal.id = newModalId;
                console.log(`✏️ Updated modal ID to ${newModalId}`);
                
                // Update button target
                containerButton.setAttribute('data-bs-target', `#${newModalId}`);
                console.log(`✏️ Updated container button target to #${newModalId}`);
                
                // Update input target
                if (countedQuantityInput) {
                    countedQuantityInput.setAttribute('data-bs-target', `#${newModalId}`);
                    console.log(`✏️ Updated counted quantity input target to #${newModalId}`);
                }
                
                // Update modal title ID
                const modalTitle = modal.querySelector('.modal-title');
                if (modalTitle) {
                    modalTitle.id = `${newModalId}Label`;
                    console.log(`✏️ Updated modal title ID to ${newModalId}Label`);
                }
                
                // Update aria-labelledby attribute on the modal
                modal.setAttribute('aria-labelledby', `${newModalId}Label`);
            }
            
            // 3. Double-check the button targets the correct modal
            const buttonTarget = containerButton.getAttribute('data-bs-target');
            if (buttonTarget !== `#${modal.id}`) {
                console.warn(`⚠️ Container button target needs correction: ${buttonTarget} → #${modal.id}`);
                containerButton.setAttribute('data-bs-target', `#${modal.id}`);
            }
            
            // 4. Ensure counted quantity input also targets the correct modal
            if (countedQuantityInput) {
                const inputTarget = countedQuantityInput.getAttribute('data-bs-target');
                if (inputTarget !== `#${modal.id}`) {
                    console.warn(`⚠️ Counted quantity input target needs correction: ${inputTarget} → #${modal.id}`);
                    countedQuantityInput.setAttribute('data-bs-target', `#${modal.id}`);
                }
            }
            
            // 5. Check for and clear existing click handlers to prevent duplicates
            if (jQuery) {
                try {
                    $(containerButton).off('click'); // Clear any previous handlers
                    $(countedQuantityInput).off('click');
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
        
        // Checkbox change handler
        $(rowElement).find('input.counted-input').off('change').on('change', function() {
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
            updateCheckBoxCellColors();
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
        $('input.counted-input').change(function(){
            sendCountRecordChange($(this), thisCountListWebSocket, 'NoContainerChange');
            updateCheckBoxCellColors();
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
            this.changeNavColor();
            this.checkRefreshStatus();
            this.setUpConnectionStatusCheck();
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
        if (location.href.includes('localhost')){
            $("#theNavBar").removeClass('bg-primary');
            $("#theNavBar").prop('style', 'background-color:#ffa500;');
        };
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
            let lotNumber = $(this).parent().parent().find('td:eq(4)').text();
            let encodedLotNumber = btoa(lotNumber)
            let tank = $(this).val();
            let encodedTank = btoa(tank);
            let blendArea = new URL(window.location.href).searchParams.get("blend-area");
            let tankUpdateResult;
            $.ajax({
                url: `/core/update-scheduled-blend-tank?encodedLotNumber=${encodedLotNumber}&encodedTank=${encodedTank}&blendArea=${blendArea}`,
                async: false,
                dataType: 'json',
                success: function(data) {
                    tankUpdateResult = data;
                }
            });
            console.log(tankUpdateResult)
        });
    };
    addHxLotNumbers() {
        
    };

};

export class ItemsToCountPage {
    constructor() {
        try {
            this.setupEventListeners();
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners(){
        // Event listener to show the dropdown and submit button
        $(".editIcon").click(function(e) {
            let thisItemId = $(this).attr("data-itemid");
            let thisItemCode = $(this).attr("data-itemcode");
            let thisAuditGroup = $(this).attr("data-auditgroup");
            $('#confirmChangeAuditGroup').attr("data-itemid", thisItemId);
            $('#confirmChangeAuditGroup').attr("data-auditgroup", thisAuditGroup);
            $("#itemCodeHeader").text(`Change Audit Group for ${thisItemCode}`);
            document.getElementById('changeAuditGroupDialog').showModal();
        });

        // Event listener to show the dialog when the custom option is selected
        $('.auditGroupDropdown').on('change', function(e) {
            const newAuditGroup = document.getElementById('customAuditGroupInput').value;
            const selectedValue = this.value;
            $('#confirmChangeAuditGroup').attr("data-auditgroup", selectedValue);
        });

        // Event listener for the custom group input
        $('#customAuditGroupInput').on('keyup', function() {
            $('#confirmChangeAuditGroup').attr("data-auditgroup", $(this).val());
        });

        // Clear the dropdown filter when user clicks into the input filter field
        $("#id_filter_criteria").on("focus", function(){
            // const selectElement = document.getElementById("auditGroupLinks");
            // selectElement.selectedIndex = 0;
            $("#auditGroupLinks").val("");
            
        });

        // Event listener for the "Confirm" button
        $('#confirmChangeAuditGroup').click(function(){
            let newAuditGroup = $(this).attr("data-auditgroup");
            let recordType = getURLParameter('recordType');
            let itemID = $(this).attr("data-itemid");
            let changeGroupURL = `/prodverse/add-item-to-new-group?redirectPage=items-to-count&auditGroup=${newAuditGroup}&recordType=${recordType}&itemID=${itemID}`;
            if (newAuditGroup.trim() !== '') { // make sure the audit group isn't blank
                window.location.replace(changeGroupURL);
            } else {
                alert('Please enter a valid audit group value.');
            };
        });

        // Event listener for the "Cancel" button
        $('#cancelChangeAuditGroup').on('click', function() {
            document.getElementById('changeAuditGroupDialog').close();
            $("#itemCodeHeader").text("");
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
        document.querySelectorAll(".collectionNameElement").forEach(inputElement => {
            inputElement.addEventListener("keyup",function(){
                console.log("event happend")
                const collectionId = inputElement.getAttribute("collectionlinkitemid");
                const newName = inputElement.value;
                thisCountCollectionWebSocket.updateCollection(collectionId, newName);
            });
        });
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
                            const deleteButton = addedNode.querySelector('.deleteCountLinkButton');
                            if (deleteButton) {
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