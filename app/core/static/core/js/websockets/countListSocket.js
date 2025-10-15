import { BaseSocket } from '../../../shared/js/websockets/BaseSocket.js';
import { StateCache } from '../../../shared/js/websockets/StateCache.js';
import {
    buildWebSocketUrl,
    extractUniqueIdFromUrl,
    sanitizeForJson,
    updateConnectionIndicator,
} from '../../../shared/js/websockets/helpers.js';
import { getURLParameter } from '../requestFunctions/requestFunctions.js';

const CONNECTION_INDICATOR = {
    connected: 'connected',
    disconnected: 'disconnected',
};

function withStatusIndicator(callback, indicator = CONNECTION_INDICATOR) {
    return (status) => {
        if (status === 'connected') {
            updateConnectionIndicator(indicator.connected);
        } else if (
            status === 'disconnected' ||
            status === 'error' ||
            status === 'closed'
        ) {
            updateConnectionIndicator(indicator.disconnected);
        }
        if (typeof callback === 'function') {
            callback(status);
        }
    };
}

export class CountListWebSocket extends BaseSocket {
    constructor(listIdOrUrl, options = {}) {
        const target = CountListWebSocket._resolveConnectionTarget(listIdOrUrl);
        super({
            resolveUrl: () => target.url,
            onStatusChange: withStatusIndicator(options.onStatusChange),
            onError: (error) => {
                console.error('CountListWebSocket error:', error);
                if (typeof options.onError === 'function') {
                    options.onError(error);
                }
            },
        });

        this.listIdentifier = target.identifier;
        this.stateCache = new StateCache();
        this.receivedMessages = new Map();
        this.sentMessages = new Map();

        window.thisCountListWebSocket = this;
    }

    static _resolveConnectionTarget(input) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        let effectiveInput = input;

        if (effectiveInput === undefined || effectiveInput === null || effectiveInput === '') {
            effectiveInput = getURLParameter('listId');
        }

        if (effectiveInput && /^wss?:\/\//i.test(effectiveInput)) {
            return {
                url: effectiveInput,
                identifier: extractUniqueIdFromUrl(effectiveInput),
            };
        }

        if (typeof effectiveInput === 'string' && effectiveInput.startsWith('/')) {
            const url = `${protocol}//${host}${effectiveInput}`;
            return {
                url,
                identifier: extractUniqueIdFromUrl(url),
            };
        }

        if (effectiveInput === undefined || effectiveInput === null || effectiveInput === '') {
            console.warn('⚠️ CountListWebSocket: No listId provided; defaulting to global route.');
            const url = `${protocol}//${host}/ws/count_list/`;
            return { url, identifier: null };
        }

        const sanitizedId = String(effectiveInput).replace(/^\/+|\/+$/g, '');
        return {
            url: buildWebSocketUrl('ws/count_list', sanitizedId),
            identifier: sanitizedId,
        };
    }

    _transmit(payload) {
        try {
            this.sendJson(payload);
            return true;
        } catch (error) {
            console.error('Error sending count list websocket message:', error);
            updateConnectionIndicator(CONNECTION_INDICATOR.disconnected);
            return false;
        }
    }

    handleMessage(payload) {
        if (!payload || typeof payload !== 'object') {
            return;
        }

        if (payload.type === 'initial_state') {
            this._applyInitialState(payload.events);
            return;
        }

        if (!payload.type) {
            return;
        }

        const cachedPayload = { ...payload };
        delete cachedPayload.senderToken;
        delete cachedPayload.sender_channel_name;

        if (!this.stateCache) {
            this.stateCache = new StateCache();
        }

        this.stateCache.recordEvent({
            event: payload.type,
            data: sanitizeForJson(cachedPayload),
        });

        this._dispatchEvent(payload.type, payload);
    }

    _applyInitialState(events = []) {
        if (!Array.isArray(events) || events.length === 0) {
            return;
        }
        if (!this.stateCache) {
            this.stateCache = new StateCache();
        }
        this.stateCache.loadSnapshot(events);
        events.forEach((entry) => {
            if (!entry || !entry.event) {
                return;
            }
            const payload = {
                type: entry.event,
                ...(entry.data || {}),
            };
            this._dispatchEvent(entry.event, payload);
        });
    }

    _dispatchEvent(eventType, payload) {
        switch (eventType) {
            case 'count_updated':
                this.updateCountUI(payload.record_id, payload);
                break;
            case 'on_hand_refreshed':
                this.updateOnHandUI(payload.record_id, payload.new_on_hand);
                break;
            case 'count_deleted':
                this.deleteCountFromUI(payload.record_id);
                break;
            case 'count_added':
                this.addCountRecordToUI(payload.record_id, payload);
                break;
            default:
                break;
        }
    }

    updateCount(recordId, recordType, recordInformation) {
        try {
            // Add a flag to indicate this is a delete operation
            if (recordInformation['containerId'] && recordInformation['action_type'] === 'delete') {
                // This helps the server identify proper ordering of messages
                recordInformation.is_delete_operation = true;
            }

            // CRITICAL FIX: Add unique message ID to prevent duplicate processing
            const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

            // Send the update via WebSocket
            const payload = {
                action: 'update_count',
                record_id: recordId,
                counted_quantity: recordInformation['counted_quantity'],
                sage_converted_quantity: recordInformation['sage_converted_quantity'],
                expected_quantity: recordInformation['expected_quantity'],
                variance: recordInformation['variance'],
                counted_date: recordInformation['counted_date'],
                counted: recordInformation['counted'],
                comment: recordInformation['comment'],
                location: recordInformation['location'],
                containers: recordInformation['containers'],
                containerId: recordInformation['containerId'],
                record_type: recordType,
                action_type: recordInformation['action_type'] || 'update',
                is_delete_operation: recordInformation['is_delete_operation'] || false,
                client_timestamp: Date.now(),
                message_id: messageId
            };
            if (!this._transmit(payload)) {
                return;
            }

            // Track sent messages for reference
            this.sentMessages.set(messageId, {
                action_type: recordInformation['action_type'] || 'update',
                timestamp: Date.now(),
                containerId: recordInformation['containerId'],
                container_count: recordInformation['containers'].length
            });
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionIndicator(CONNECTION_INDICATOR.disconnected);
        }
    }

    refreshOnHand(recordId, recordType) {
        try {
            const payload = {
                action: 'refresh_on_hand',
                record_id: recordId,
                record_type: recordType
            };
            this._transmit(payload);
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionIndicator(CONNECTION_INDICATOR.disconnected);
        }
    }

    deleteCount(recordId, recordType, listId) {
        try {
            const payload = {
                action: 'delete_count',
                record_id: recordId,
                record_type: recordType,
                list_id: listId
            };
            this._transmit(payload);
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionIndicator(CONNECTION_INDICATOR.disconnected);
        }
    }

    addCount(recordType, listId, itemCode) {
        try {
            const payload = {
                action: 'add_count',
                record_type: recordType,
                list_id: listId,
                item_code: itemCode
            };
            this._transmit(payload);
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionIndicator(CONNECTION_INDICATOR.disconnected);
        }
    }

    updateCountUI(recordId, data) {
        // Extract message ID for tracking and anti-duplication
        const messageId = data.data.message_id || `auto_${Date.now()}`;
        
        // CRITICAL FIX: Track received messages to prevent duplicate processing
        if (!this.receivedMessages) this.receivedMessages = new Map();
        
        // Check if we've already processed this message or a very similar one
        const recentMessages = Array.from(this.receivedMessages.values())
            .filter(msg => (
                msg.timestamp > Date.now() - 2000 && // Messages in the last 2 seconds
                msg.recordId === recordId && 
                msg.containerId === data.data.containerId
            ));
            
        // Handle potential race conditions with delete operations
        if (recentMessages.length > 0) {
            const isSequentialDelete = data.data.action_type === 'delete' && 
                                      recentMessages.some(msg => msg.action_type === 'delete');
            
            if (isSequentialDelete && Date.now() - recentMessages[0].timestamp < 300) {
                console.warn(`🚫 Preventing duplicate delete processing for record ${recordId}`);
                return; // Skip processing this message entirely
            }
        }
        
        // Record this message as processed
        this.receivedMessages.set(messageId, {
            recordId: recordId,
            action_type: data.data.action_type,
            containerId: data.data.containerId,
            timestamp: Date.now()
        });
        
        // Limit the size of the received messages map
        if (this.receivedMessages.size > 100) {
            const oldestKey = Array.from(this.receivedMessages.keys())[0];
            this.receivedMessages.delete(oldestKey);
        }
        
        try {
            // Update counted quantity from server data
            let countedQuantity = data['data']['counted_quantity'];
            if (countedQuantity) {
                const formattedQuantity = parseFloat(countedQuantity).toFixed(4);
                
                // Update using primary selector - most reliable approach
                const $countedQuantityInput = $(`input.counted_quantity[data-countrecord-id="${recordId}"]`);
                if ($countedQuantityInput.length > 0) {
                    $countedQuantityInput.val(formattedQuantity);
                }
                
                // Update variance from server data
                const variance = data['data']['variance'];
                if (variance) {
                    const $varianceCell = $(`td[data-countrecord-id="${recordId}"].tbl-cell-variance`);
                    if ($varianceCell.length > 0) {
                        $varianceCell.text(variance);
                    }
                }
            }

            // Update counted_date from server data
            const countedDate = data['data']['counted_date'];
            if (countedDate) {
                const $countedDateCell = $(`td[data-countrecord-id="${recordId}"].tbl-cell-counted_date`);
                if ($countedDateCell.length > 0) {
                    $countedDateCell.text(countedDate);
                }
            }

            // Update comment from server data
            // Check if 'comment' exists and is not null, then update
            if (data['data'].hasOwnProperty('comment') && data['data']['comment'] !== null) {
                const comment = data['data']['comment'];
                const $commentTextarea = $(`textarea.comment[data-countrecord-id="${recordId}"]`);
                if ($commentTextarea.length > 0) {
                    $commentTextarea.val(comment);
                }
            }

            // Update location from server data
            // Check if 'location' exists and is not null, then update
            if (data['data'].hasOwnProperty('location') && data['data']['location'] !== null) {
                const location = data['data']['location'];
                const $locationSelector = $(`select.location-selector[data-countrecord-id="${recordId}"]`);
                if ($locationSelector.length > 0) {
                    $locationSelector.val(location);
                }
            }

            // Update counted (approved checkbox) state from server data
            if (data['data'].hasOwnProperty('counted')) {
                const counted = data['data']['counted'];
                const $countedCheckbox = $(`input.counted-input[data-countrecord-id="${recordId}"]`);
                const $countedCell = $(`td.tbl-cell-counted[data-countrecord-id="${recordId}"]`);

                if ($countedCheckbox.length > 0) {
                    $countedCheckbox.prop('checked', counted);
                }
                
                // Directly update the cell's class
                if ($countedCell.length > 0) {
                    if (counted) {
                        $countedCell.removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
                    } else {
                        $countedCell.removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
                    }
                }

                // Update the row's class as well (for mobile or other styling)
                const $row = $(`tr.countRow[data-countrecord-id="${recordId}"]`);
                if ($row.length > 0) {
                    if (counted) {
                        $row.addClass('approved');
                    } else {
                        $row.removeClass('approved');
                    }
                }
            }

        } catch (err) {
            console.error(`Error updating quantity/variance/other fields:`, err);
        }
        
        // Process container updates from server
        try {
            if (data['data']['containers'] && Array.isArray(data['data']['containers'])) {
                // CRITICAL FIX: Flag delete operations for special handling
                const isDeleteOperation = data['data']['action_type'] === 'delete' || 
                                         data['data']['is_delete_operation'] === true;
                
                if (window.countListPage && window.countListPage.containerManager) {
                    // Update the container cache with server data
                    window.countListPage.containerManager.cachedContainers.set(recordId, data['data']['containers']);
                    
                    // If modal is open, refresh the container display
                    const openModal = document.querySelector(`#containersModal${recordId}.show, .modal.emergency-show[id="containersModal${recordId}"]`);
                    if (openModal) {
                        const containerTableBody = $(openModal).find('tbody.containerTbody');
                        if (containerTableBody.length > 0) {
                            // Render the container rows with the fresh server data
                            // Pass isDeleteOperation flag to prevent auto-creating empty containers
                            window.countListPage.containerManager.renderContainerRows(
                                recordId, 
                                data['data']['record_type'] || getURLParameter('recordType') || 'blendcomponent', 
                                containerTableBody,
                                {isDeleteOperation: isDeleteOperation}
                            );
                        }
                    }
                }
            }
        } catch (containerErr) {
            console.error(`Error handling container data:`, containerErr);
        }
    }

    updateOnHandUI(recordId, newOnHand) {
        $(`span[data-countrecord-id="${recordId}"]`).text(parseFloat(newOnHand).toFixed(4));
    }

    deleteCountFromUI(recordId) {
        $(`tr[data-countrecord-id="${recordId}"]`).remove()
    }

    addCountRecordToUI(recordId, data) {
        try {
            // Hide modal if open
            if ($('#addCountListItemModal').hasClass('show')) {
                $('#addCountListItemModal').modal('hide');
            }
            
            // Check if table exists before proceeding
            this._checkTableStructure('BEFORE');
            
            // Get the table
            const table = document.getElementById('countsTable');
            if (!table) {
                console.error("Cannot find table for insertion");
                return false;
            }
            
            // Find the table body
            const tbody = table.querySelector('tbody');
            if (!tbody) {
                console.error("Cannot find tbody for insertion");
                return false;
            }
            
            // Look for an existing row to clone as a template
            const existingRow = tbody.querySelector('tr.countRow');
            if (existingRow) {
                const success = this._createRowByCloning(existingRow, recordId, data, tbody);
                
                if (success) {
                    // Access the ContainerManager through the countListPage instance
                    if (window.countListPage && window.countListPage.containerManager) {
                        const recordType = getURLParameter('recordType') || 'blendcomponent';
                        
                        // First find the container table body for this record
                        const containerTableBodyElement = document.querySelector(`table.container-table[data-countrecord-id="${recordId}"] tbody.containerTbody`);
                        
                        if (containerTableBodyElement) {
                            // Wrap the DOM element in jQuery before passing it to renderContainerRows
                            const $containerTableBody = $(containerTableBodyElement);
                            
                            // Render the container rows for this record
                            try {
                                window.countListPage.containerManager.renderContainerRows(recordId, recordType, $containerTableBody);
                            } catch (error) {
                                console.error(`❌ Error rendering container rows:`, error);
                            }
        } else {
                            console.error(`❌ Container table body not found for record ${recordId}`);
                        }
                    } else {
                        console.error("🚨 ContainerManager not found via window.countListPage - containers will not function!");
                    }
                    
                    // Set a timeout to check if the row is actually visible after insertion
                    setTimeout(() => this._checkTableStructure('AFTER', recordId), 1000);
                    return true;
                }
            }
            
            return false;
        } catch (error) {
            console.error("Error adding count record to UI:", error);
            return false;
        }
    }
    
    _createRowByCloning(templateRow, recordId, data, tbody) {
        try {
            // Clone the existing row for perfect structure preservation
            const newRow = templateRow.cloneNode(true);
            newRow.setAttribute('data-countrecord-id', recordId);
            
            // Update all data-countrecord-id attributes inside the new row
            const elementsWithDataAttr = newRow.querySelectorAll('[data-countrecord-id]');
            elementsWithDataAttr.forEach(el => {
                el.setAttribute('data-countrecord-id', recordId);
            });
            
            // Update specific fields with the new data
            const itemCodeLink = newRow.querySelector('.itemCodeDropdownLink');
            if (itemCodeLink) itemCodeLink.textContent = data.item_code;
            
            const partialContainerLink = newRow.querySelector('.partialContainerLabelLink');
            if (partialContainerLink) partialContainerLink.setAttribute('data-itemcode', data.item_code);
            
            const descriptionCell = newRow.querySelector('.tbl-cell-item_description');
            if (descriptionCell) descriptionCell.textContent = data.item_description || '';
            
            const expectedQtySpan = newRow.querySelector('.expected-quantity-span');
            if (expectedQtySpan) expectedQtySpan.textContent = parseFloat(data.expected_quantity || 0).toFixed(4);
            
            const qtyRefreshButton = newRow.querySelector('.qtyrefreshbutton');
            if (qtyRefreshButton) qtyRefreshButton.setAttribute('itemcode', data.item_code);
            
            // Use standardized modal IDs
            const containerButton = newRow.querySelector('.containers');
            if (containerButton) containerButton.setAttribute('data-bs-target', `#containersModal${recordId}`);
            
            const containerModal = newRow.querySelector('.modal');
            if (containerModal) containerModal.id = `containersModal${recordId}`;
            
            const containerModalLabel = newRow.querySelector('.modal-title');
            if (containerModalLabel) containerModalLabel.id = `containersModalLabel${recordId}`;
            if (containerModalLabel) containerModalLabel.innerHTML = `Containers for ${data.item_code}: <p class="containerQuantity"></p>`;
            
            const countedQtyInput = newRow.querySelector('.counted_quantity');
            if (countedQtyInput) {
                countedQtyInput.value = parseFloat(data.counted_quantity || 0).toFixed(0);
                countedQtyInput.setAttribute('data-bs-target', `#containersModal${recordId}`);
            }
            
            const countedDateCell = newRow.querySelector('.tbl-cell-counted_date');
            if (countedDateCell) countedDateCell.textContent = data.counted_date || '';
            
            const varianceCell = newRow.querySelector('.tbl-cell-variance');
            if (varianceCell) varianceCell.textContent = parseFloat(data.variance || 0).toFixed(0);
            
            const countedCell = newRow.querySelector('.tbl-cell-counted');
            if (countedCell) {
                if (data.counted) {
                    countedCell.classList.remove('uncheckedcountedcell');
                    countedCell.classList.add('checkedcountedcell');
                } else {
                    countedCell.classList.remove('checkedcountedcell');
                    countedCell.classList.add('uncheckedcountedcell');
                }
            }
            
            const countedCheckbox = newRow.querySelector('.counted-input');
            if (countedCheckbox) countedCheckbox.checked = data.counted;
            
            const commentTextarea = newRow.querySelector('.comment');
            if (commentTextarea) commentTextarea.value = data.comment || 'None';
            
            const discardButton = newRow.querySelector('.discardButton');
            if (discardButton) discardButton.setAttribute('data-countlist-id', getURLParameter('listId'));
            
            // Find the "Add Item" row if it exists
            const addItemRow = Array.from(tbody.querySelectorAll('tr')).find(row => 
                row.querySelector('button[data-bs-target="#addCountListItemModal"]') || 
                row.querySelector('#modalToggle')
            );
            
            // Insert before add item row or at the end
            if (addItemRow) {
                tbody.insertBefore(newRow, addItemRow);
            } else {
                tbody.appendChild(newRow);
            }
            
            // Highlight the new row
            $(newRow).css({
                'backgroundColor': '#ffffcc',
                'transition': 'background-color 2s'
            });
            
            setTimeout(() => {
                $(newRow).css('backgroundColor', '');
                
                // Ensure modal bindings are correct before reinitializing
                const bindingSuccess = this._ensureProperModalBindings(newRow, recordId);
                
                // Reinitialize Bootstrap components on the new row
                this._reinitializeBootstrap(newRow);
                
                // Copy event handlers from other rows
                this._copyAllEventHandlers(tbody, newRow, recordId);
                
                // Scroll to make visible
                newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
            
            // Update quantity - ensure proper formatting and handling
            const quantityCell = newRow.querySelector('.quantity-cell, td.quantity-cell');
            if (quantityCell) {
                if (data.quantity !== undefined && data.quantity !== null && data.quantity !== '') {
                    const quantityValue = parseFloat(data.quantity);
                    if (!isNaN(quantityValue)) {
                        const quantityText = `${quantityValue.toFixed(1)} gal`;
                        quantityCell.textContent = quantityText;
                    } else {
                        quantityCell.textContent = '0.0 gal';
                        console.warn(`⚠️ Invalid quantity value: ${data.quantity}, defaulting to 0.0 gal`);
                    }
                } else {
                    quantityCell.textContent = '0.0 gal';
                    console.warn(`⚠️ No quantity data provided, defaulting to 0.0 gal`);
                }
            } else {
                console.warn(`⚠️ Could not find quantity cell in new row`);
            }
            
            return true;
        } catch (error) {
            console.error("Row cloning failed:", error);
            return false;
        }
    }
    
    _reinitializeBootstrap(row) {
        try {
            // Find all Bootstrap components and reinitialize them
            
            // 1. Dropdowns
            const dropdowns = row.querySelectorAll('[data-bs-toggle="dropdown"]');
            dropdowns.forEach(dropdown => {
                if (window.bootstrap && window.bootstrap.Dropdown) {
                    new window.bootstrap.Dropdown(dropdown);
                }
            });
            
            // 2. Modals
            const modalTriggers = row.querySelectorAll('[data-bs-toggle="modal"]');
            modalTriggers.forEach(trigger => {
                if (window.bootstrap && window.bootstrap.Modal) {
                    // Get the target modal ID
                    const targetId = trigger.getAttribute('data-bs-target');
                    if (targetId) {
                        // Ensure the modal exists in the DOM
                        let modal = document.querySelector(targetId);
                        if (modal) {
                            new window.bootstrap.Modal(modal);
                        } else {
                            console.warn(`Modal ${targetId} not found for initialization`);
                        }
                    }
                }
            });
            
        } catch (error) {
            console.warn("Bootstrap reinitialization failed:", error);
        }
    }
    
    _ensureProperModalBindings(row, recordId) {
        try {
            // Get our target modal
            const containerCell = row.querySelector('.tbl-cell-containers');
            if (!containerCell) {
                console.error("Cannot find container cell in row");
                return false;
            }
            
            const containerButton = containerCell.querySelector('button.containers');
            if (!containerButton) {
                console.error("Cannot find container button in row");
                return false;
            }
            
            const modal = containerCell.querySelector('.modal');
            if (!modal) {
                console.error("Cannot find modal in container cell");
                return false;
            }
            
            // Ensure the modal has the exact expected ID format
            const uniqueModalId = `containersModal${recordId}`;
            modal.id = uniqueModalId;
            
            // Update references to the modal from outside
            containerButton.setAttribute('data-bs-target', `#${uniqueModalId}`);
            
            // Update the counted quantity input
            const countedQtyInput = row.querySelector('.counted_quantity');
            if (countedQtyInput) {
                countedQtyInput.setAttribute('data-bs-target', `#${uniqueModalId}`);
            }
            
            // Rely on Bootstrap's built-in modal behavior instead of custom handlers
            // This eliminates a source of double bindings
            containerButton.setAttribute('data-bs-toggle', 'modal');
            if (countedQtyInput) {
                countedQtyInput.setAttribute('data-bs-toggle', 'modal');
            }
            return true;
        } catch (error) {
            console.error("Error during modal binding:", error);
            return false;
        }
    }

    _copyAllEventHandlers(tbody, targetRow, recordId) {
        try {
            // Find an existing row to copy handlers from
            const sourceRow = Array.from(tbody.querySelectorAll('tr.countRow')).find(row => 
                row !== targetRow && row.hasAttribute('data-countrecord-id')
            );
            
            if (!sourceRow) {
                console.warn("Could not find source row for event handler copying");
                return;
            }
            
            // Copy button click handlers
            const buttons = ['button.containers', 'i.qtyrefreshbutton', 'i.discardButton'];
            buttons.forEach(selector => {
                const sourceButton = sourceRow.querySelector(selector);
                const targetButton = targetRow.querySelector(selector);
                
                if (sourceButton && targetButton) {
                    const events = $._data(sourceButton, 'events');
                    if (events && events.click) {
                        events.click.forEach(event => {
                            $(targetButton).on('click', event.handler);
                        });
                    }
                }
            });
            
            // Copy input handlers for checkboxes and textareas
            const inputs = ['input.counted-input', 'textarea.comment', 'select.location-selector'];
            const events = ['change', 'input', 'blur', 'focus'];
            
            inputs.forEach(selector => {
                const sourceInput = sourceRow.querySelector(selector);
                const targetInput = targetRow.querySelector(selector);
                
                if (sourceInput && targetInput) {
                    events.forEach(eventType => {
                        const eventData = $._data(sourceInput, 'events');
                        if (eventData && eventData[eventType]) {
                            eventData[eventType].forEach(event => {
                                $(targetInput).on(eventType, event.handler);
                            });
                        }
                    });
                }
            });
            
        } catch (error) {
            console.warn("Event handler copying failed:", error);
        }
    }

    _checkTableStructure(phase, newRowId = null) {
        try {
            const table = document.getElementById('countsTable');
            if (!table) {
                return;
            }
            
            const tbody = table.querySelector('tbody');
            if (!tbody) {
                return;
            }
            
            const rows = tbody.querySelectorAll('tr');
            
            // Look for Add Item row
            const addItemRow = Array.from(rows).find(row => 
                row.querySelector('button[data-bs-target="#addCountListItemModal"]') || 
                row.querySelector('#modalToggle')
            );
            
            // Check for the new row if in AFTER phase
            if (phase === 'AFTER' && newRowId) {
                const newRow = tbody.querySelector(`tr[data-countrecord-id="${newRowId}"]`);
                if (newRow) {
                    // Check row visibility
                    const rowStyle = window.getComputedStyle(newRow);
                } else {
                    return;
                }
            }
        } catch (e) {
            return;
        }
    }
}


if (typeof window !== "undefined") {
    window.CountListWebSocket = CountListWebSocket;
}
