import { getContainersFromCount, getURLParameter } from '../requestFunctions/requestFunctions.js'

// Global debug function to force table refresh
window.debugRefreshTable = function() {
    const table = document.getElementById('countsTable');
    if (table) {
        // Hide and show to force reflow
        table.style.display = 'none';
        void table.offsetHeight;
        table.style.display = '';
        
        // Flash the table to indicate refresh
        table.style.backgroundColor = '#ffff99';
        setTimeout(() => {
            table.style.backgroundColor = '';
        }, 500);
    } else {
        console.error("❌ Could not find table to refresh");
    }
};

function updateConnectionStatus(status) {
    const connectionStatusElement = document.getElementById('connectionStatusIndicator');
    if (connectionStatusElement) {
        connectionStatusElement.className = status;
        const spanElement = connectionStatusElement.querySelector('span');
        if (status == 'connected') {
            if (spanElement) {
                spanElement.innerHTML = '&#10003;';
            };
            connectionStatusElement.innerHTML = spanElement.outerHTML + ' Connected';
        } else if (status == 'disconnected') {
            if (spanElement) {
                spanElement.innerHTML = '&#10007;';
            };
            connectionStatusElement.innerHTML = spanElement.outerHTML + ' Disconnected';
        };
    };   
};

export class CountListWebSocket {
    constructor(url) {
        try {
            this.socket = new WebSocket(url);
            this.initEventListeners();
            
            // Make WebSocket instance globally accessible for emergency communications
            window.thisCountListWebSocket = this;
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
            updateConnectionStatus('disconnected');
        }
    }

    initEventListeners() {
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'count_updated') {
                this.updateCountUI(data.record_id, data);
            } else if (data.type === 'on_hand_refreshed') {
                this.updateOnHandUI(data.record_id, data.new_on_hand);
            } else if (data.type === 'count_deleted') {
                this.deleteCountFromUI(data.record_id);
            } else if (data.type === 'count_added') {
                this.addCountRecordToUI(data.record_id, data);
            }
        };

        this.socket.onclose = () => {
            console.error('Count list socket closed unexpectedly');
            updateConnectionStatus('disconnected');
            this.reconnect();
        };
    }

    reconnect() {
        // Clear any existing reconnect timers
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        
        // Track reconnection attempts
        if (!this._reconnectAttempts) {
            this._reconnectAttempts = 0;
        }
        this._reconnectAttempts++;
        
        // Add some backoff for subsequent attempts (max 10 seconds)
        const delay = Math.min(1000 * Math.pow(1.5, this._reconnectAttempts - 1), 10000);
        
        this._reconnectTimer = setTimeout(() => {
            try {
                // Use the same protocol as the page
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                
                // Build the URL correctly
                let url;
                try {
                    url = new URL(this.socket.url);
            url.protocol = protocol;
                } catch (urlError) {
                    // If the socket URL isn't valid, try to reconstruct from the current page
                    url = new URL(`${protocol}//${window.location.host}/ws/count_list/`);
                    console.warn(`⚠️ Had to reconstruct WebSocket URL: ${url.toString()}`);
                }
                
                // Close existing socket if it's still around
                if (this.socket) {
                    try {
                        // Remove existing event handlers to prevent duplicates
                        this.socket.onclose = null;
                        this.socket.onerror = null;
                        this.socket.onmessage = null;
                        
                        // Force close if still open
                        if (this.socket.readyState !== WebSocket.CLOSED) {
                            this.socket.close();
                        }
                    } catch (closeError) {
                        console.warn(`Error closing old socket:`, closeError);
                    }
                }
                
                // Create new socket
            this.socket = new WebSocket(url.toString());
                
                // Set up event handlers
            this.initEventListeners();
                
                // Add special onopen handler for this reconnection
            this.socket.onopen = () => {
                updateConnectionStatus('connected');
                    
                    // Reset reconnect attempts on success
                    this._reconnectAttempts = 0;
                    this._reconnectTimer = null;
                    
                    // Add a ping mechanism to keep connection alive
                    if (this._pingInterval) {
                        clearInterval(this._pingInterval);
                    }
                    
                    // Send ping every 30 seconds to keep connection alive
                    this._pingInterval = setInterval(() => {
                        if (this.socket.readyState === WebSocket.OPEN) {
                            try {
                                // Send a harmless ping message
                                this.socket.send(JSON.stringify({
                                    action: 'ping',
                                    timestamp: Date.now()
                                }));
                            } catch (pingError) {
                                console.warn(`Error sending ping:`, pingError);
                                // If ping fails, try to reconnect
                                this.reconnect();
                            }
                        } else {
                            // If not open, try to reconnect
                            console.warn(`⚠️ WebSocket not open during ping check (state: ${this.socket.readyState})`);
                            this.reconnect();
                        }
                    }, 30000);
                };
                
                // Add special onerror handler for this reconnection
                this.socket.onerror = (error) => {
                    console.error(`❌ WebSocket reconnection error:`, error);
                    updateConnectionStatus('disconnected');
                    
                    // Try again with increasing backoff
                    this.reconnect();
                };
            } catch (error) {
                console.error('Fatal error during WebSocket reconnection:', error);
                updateConnectionStatus('disconnected');
                
                // Even after fatal error, try again
                this._reconnectTimer = setTimeout(() => {
                    this.reconnect();
                }, 5000);
            }
        }, delay);
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
            this.socket.send(JSON.stringify({
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
            }));

            // Track sent messages for reference
            if (!this.sentMessages) this.sentMessages = new Map();
            this.sentMessages.set(messageId, {
                action_type: recordInformation['action_type'] || 'update',
                timestamp: Date.now(),
                containerId: recordInformation['containerId'],
                container_count: recordInformation['containers'].length
            });
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionStatus('disconnected');
        }
    }

    refreshOnHand(recordId, recordType) {
        try{
            this.socket.send(JSON.stringify({
                action: 'refresh_on_hand',
                record_id: recordId,
                record_type: recordType
            }));
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionStatus('disconnected');
        }
    }

    deleteCount(recordId, recordType, listId) {
        try {
            this.socket.send(JSON.stringify({
                action: 'delete_count',
                record_id: recordId,
                record_type: recordType,
                list_id: listId
            }));
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionStatus('disconnected');
        }
    }

    addCount(recordType, listId, itemCode) {
        try {
            this.socket.send(JSON.stringify({
                action: 'add_count',
                record_type: recordType,
                list_id: listId,
                item_code: itemCode
            }));
        } catch (error) {
            console.error('Error sending update_count message:', error);
            updateConnectionStatus('disconnected');
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

export class CountCollectionWebSocket {
    constructor() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/count_collection/`);
        this.initEventListeners();
    }

    initEventListeners() {
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
            console.log(data.type);
            
            if (data.type === 'collection_updated') {
                this.updateCollectionUI(data.collection_id, data.new_name);
            } else if (data.type === 'collection_deleted') {
                this.removeCollectionUI(data.collection_id);
            } else if (data.type === 'collection_added') { 
                this.addCollectionUI(data);
            } else if (data.type === 'collection_order_updated') {
                this.updateCollectionOrderUI(data.updated_order);
            }
        };

        this.socket.onclose = () => {
            console.error('Count collection socket closed unexpectedly');
            updateConnectionStatus('disconnected');
            this.reconnect();
        };

        this.socket.onopen = () => {
            console.log("Count collection update WebSocket connection established.");
            this.reconnectAttempts = 0;
            updateConnectionStatus('connected');
        };

        this.socket.onerror = (error) => {
            console.error('Count collection update WebSocket error:', error);
            updateConnectionStatus('disconnected');
        };

    }

    reconnect() {
        setTimeout(() => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = new URL(this.socket.url);
            url.protocol = protocol;
            this.socket = new WebSocket(url.toString());
            this.initEventListeners();
            this.socket.onopen = () => {
                updateConnectionStatus('connected');
            };
        }, 1000);
    }

    updateCollection(collectionId, newName) {
        this.socket.send(JSON.stringify({
            action: 'update_collection',
            collection_id: collectionId,
            new_name: newName
        }));
    }

    deleteCollection(collectionId) {
        this.socket.send(JSON.stringify({
            action: 'delete_collection',
            collection_id: collectionId
        }));
    }

    updateCollectionOrder(collectionLinkDict) {
        this.socket.send(JSON.stringify({
            action: 'update_collection_order',
            collection_link_order: collectionLinkDict
        }));
    }

    updateCollectionUI(collectionId, newName) {
        $(`#input${collectionId}`).val(newName);
        console.log('blebb');
        const headerElement = document.getElementById('countListNameHeader');
        if (headerElement) {
            headerElement.textContent = newName;
        }
    }

    removeCollectionUI(collectionId) {
        console.log("removing " + collectionId);
        console.log($(`tr[collectionlinkitemid="${collectionId}"]`));
        $(`tr[collectionlinkitemid="${collectionId}"]`).remove();
    }

    addCollectionUI(data) {
        console.log('adding ' + data);
        let lastRow = $('table tr:last').clone();
        lastRow.find('td').attr('data-collection-id', data.id);
        lastRow.attr('collectionlinkitemid', data.id);
        lastRow.find('td.listOrderCell').text(data.link_order);
        lastRow.find('a.collectionLink').attr('href', `/core/count-list/display/?listId=${data.id}&recordType=${data.record_type}`);
        lastRow.find('input.collectionNameElement').val(data.collection_name);
        lastRow.find('i.deleteCountLinkButton').attr('collectionlinkitemid', data.id);
        $('#countCollectionLinkTable').append(lastRow);
        // lastRow.find('td.collectionId').text(collectionLinkInfo.collection_id);
    }

    updateCollectionOrderUI(updatedOrderPairs) {
        Object.entries(updatedOrderPairs).forEach(([collectionId, newOrder]) => {
            const row = $(`tr[collectionlinkitemid="${collectionId}"]`);
            row.find('td.listOrderCell').text(newOrder);
            row.attr('data-order', newOrder);
        });
        
        const rows = $('#countCollectionLinkTable tbody tr').get();

        rows.sort((a, b) => {
            const orderA = parseInt($(a).find('td.listOrderCell').text(), 10);
            const orderB = parseInt($(b).find('td.listOrderCell').text(), 10);
            return orderA - orderB;
        });

        $.each(rows, function(index, row) {
            $('#countCollectionLinkTable tbody').append(row);
        });
    }
}

export class BlendScheduleWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.pingInterval = null;
        this.isNavigating = false;
        this.isDragging = false; // 🎯 Initialize dragging state for sort protection
        
        this.setupNavigationDetection();
        this.initWebSocket();
    }

    setupNavigationDetection() {
        // Detect when user is navigating away from page
        window.addEventListener('beforeunload', () => {
            this.isNavigating = true;
        });
        
        // Detect when page is being hidden (tab switch, navigation, etc.)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.isNavigating = true;
            } else {
                // Re-enable after a short delay when page becomes visible again
                setTimeout(() => {
                    this.isNavigating = false;
                }, 1000);
            }
        });
        
        // Detect page load completion to re-enable processing
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => {
                    this.isNavigating = false;
                }, 2000); // Give page time to fully load
            });
        } else {
            // Page already loaded
            setTimeout(() => {
                this.isNavigating = false;
            }, 1000);
        }
    }

    initWebSocket() {
        if (this.socket) {
            this.socket.close();
        }

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/blend_schedule/`);
            
            this.socket.onopen = () => {
                updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
                this.startPing();
                
                // Make WebSocket globally accessible
                window.blendScheduleWS = this;
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error("Error parsing WebSocket message:", e, event.data);
                }
            };

            this.socket.onclose = (event) => {
                updateConnectionStatus('disconnected');
                this.stopPing();
                this.reconnect();
            };

            this.socket.onerror = (error) => {
                console.error("BlendSchedule WebSocket error:", error);
                updateConnectionStatus('disconnected');
            };

        } catch (error) {
            console.error("BlendSchedule WebSocket initialization error:", error);
            updateConnectionStatus('disconnected');
        }
    }

    handleMessage(data) {
        if (data.type === 'pong') {
            return;
        }

        // Skip processing if page is navigating to prevent duplicates
        if (this.isNavigating) {
            return;
        }

        if (data.type === 'blend_schedule_update') {
            const updateType = data.update_type;
            const updateData = data.data;

            // 🎯 ENHANCED: Page-aware filtering with special handling for "all schedules" page
            const currentPageArea = this.getCurrentPageArea();
            let shouldProcess = false;
            
            if (currentPageArea === 'all') {
                // On "all schedules" page, process updates for desk areas only
                // (Desk_1, Desk_2, LET_Desk) but not other areas like Hx, Dm, Totes
                const deskAreas = ['Desk_1', 'Desk_2', 'LET_Desk'];
                
                if (updateType === 'blend_moved') {
                    const oldArea = updateData.old_blend_area;
                    const newArea = updateData.new_blend_area;
                    shouldProcess = deskAreas.includes(oldArea) || deskAreas.includes(newArea);
                } else {
                    const updateBlendArea = updateData.blend_area || updateData.new_blend_area;
                    shouldProcess = deskAreas.includes(updateBlendArea);
                }
            } else if (updateType === 'blend_moved') {
                // For blend_moved, check both old and new areas
                const oldArea = updateData.old_blend_area;
                const newArea = updateData.new_blend_area;
                shouldProcess = (currentPageArea === oldArea || currentPageArea === newArea);
            } else {
                // For other message types, use the standard blend_area
                const updateBlendArea = updateData.blend_area || updateData.new_blend_area;
                shouldProcess = (currentPageArea === updateBlendArea);
            }
            
            if (!shouldProcess) {
                return;
            }

            switch (updateType) {
                case 'blend_status_changed':
                    this.updateBlendStatus(updateData);
                    break;
                case 'lot_updated':
                    this.updateLotInfo(updateData);
                    break;
                case 'blend_deleted':
                    this.removeBlend(updateData);
                    break;
                case 'new_blend_added':
                    this.addBlend(updateData);
                    break;
                case 'blend_moved':
                    // Extra protection against duplicates during navigation
                    if (this.isNavigating) {
                        return;
                    }
                    this.handleBlendMoved(updateData);
                    break;
                case 'tank_updated':
                    this.updateTankAssignment(updateData);
                    break;
                case 'schedule_reordered':
                    this.handleScheduleReorder(updateData);
                    break;
                case 'test_message':
                    alert(`Test WebSocket received: ${updateData.message}`);
                    break;
                default:
                    console.warn(`Unknown update type: ${updateType}`);
            }
        } else {
            console.warn("Unknown message type:", data.type);
        }
    }

    updateBlendStatus(data) {
        const blendId = data.blend_id;
        
        const statusCell = document.querySelector(`tr[data-blend-id="${blendId}"] .blend-sheet-status, tr[data-blend-id="${blendId}"] .blend-sheet-status-cell .blend-sheet-status`);
        
        if (statusCell) {
            statusCell.setAttribute('data-has-been-printed', data.has_been_printed);
            statusCell.setAttribute('data-print-history', data.print_history_json || '[]');
            statusCell.innerHTML = data.last_print_event_str;
            
            if (data.was_edited_after_last_print) {
                statusCell.innerHTML += '<sup class="edited-after-print-indicator">!</sup>';
            }
            
            // Reinitialize tooltip for this specific element after status update
            this.initializeTooltipForElement(statusCell);
            
            statusCell.style.backgroundColor = '#ffffcc';
            setTimeout(() => {
                statusCell.style.backgroundColor = '';
            }, 2000);
        } else {
            console.warn(`No status cell found for blend_id: ${blendId}`);
        }
    }

    updateLotInfo(data) {
        const blendId = data.blend_id;
        
        const lotCell = document.querySelector(`tr[data-blend-id="${blendId}"] .lot-number-cell`);
        
        if (lotCell) {
            lotCell.setAttribute('lot-number', data.lot_number);
            const lotText = lotCell.childNodes[0];
            if (lotText && lotText.nodeType === Node.TEXT_NODE) {
                lotText.textContent = data.lot_number;
            }
            
            lotCell.style.backgroundColor = '#ccffcc';
            setTimeout(() => {
                lotCell.style.backgroundColor = '';
            }, 2000);
        } else {
            console.warn(`No lot cell found for blend_id: ${blendId}`);
        }

        const quantityCell = document.querySelector(`tr[data-blend-id="${blendId}"] td.quantity-cell`);
        
        if (quantityCell && data.quantity) {
            const newQuantityText = `${parseFloat(data.quantity).toFixed(1)} gal`;
            quantityCell.textContent = newQuantityText;
            
            // Visual feedback for quantity update
            quantityCell.style.backgroundColor = '#ccffff';
            setTimeout(() => {
                quantityCell.style.backgroundColor = '';
            }, 2000);
        } else if (!quantityCell) {
            console.warn(`No quantity cell found for blend_id: ${blendId}`);
        }
    }

    updateTankAssignment(data) {
        const blendId = data.blend_id;
        const newTank = data.new_tank;
        const lotNumber = data.lot_number;
        
        // Find the row by blend_id
        const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
        if (!row) {
            console.warn(`⚠️ Could not find row for blend_id: ${blendId}`);
            return;
        }
        
        // Find the tank select dropdown in this row
        const tankSelect = row.querySelector('.tankSelect');
        if (!tankSelect) {
            console.warn(`⚠️ Could not find tank select dropdown for blend_id: ${blendId}`);
            return;
        }
        
        // Update the selected value - handle null/None properly
        if (newTank && newTank !== 'null' && newTank !== 'None') {
            tankSelect.value = newTank;
        } else {
            // No tank assigned - set to empty which should select the default "no selection" option
            tankSelect.value = '';
            
            // If that doesn't work, try to find and select the first option (usually the default)
            if (tankSelect.selectedIndex === -1 && tankSelect.options.length > 0) {
                tankSelect.selectedIndex = 0;
            }
        }
        
        // Add visual feedback to show the change
        tankSelect.style.backgroundColor = '#fff3cd'; // Light yellow
        tankSelect.style.transition = 'background-color 2s ease';
        
        setTimeout(() => {
            tankSelect.style.backgroundColor = '';
        }, 2000);
        
        // Optional: Show a subtle notification
        this.showTankUpdateNotification(lotNumber, data.old_tank, newTank);
    }

    showTankUpdateNotification(lotNumber, oldTank, newTank) {
        // Create a subtle notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 8px 12px;
            color: #856404;
            font-size: 14px;
            z-index: 9999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        
        // Format tank names for display
        const displayOldTank = oldTank || 'None';
        const displayNewTank = newTank || 'None';
        
        notification.innerHTML = `
            <strong>Tank Updated:</strong> Lot ${lotNumber}<br>
            <small>${displayOldTank} → ${displayNewTank}</small>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove notification after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    removeBlend(data) {
        const blendId = data.blend_id;
        const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
        if (row) {
            row.style.backgroundColor = '#ffcccc';
            setTimeout(() => {
                row.remove();
            }, 1000);
        }
    }

    addBlend(data) {
        const htmlRow = data.html_row;
        const blendArea = data.blend_area || data.new_blend_area;
        
        // 🎯 ENHANCED: Handle both HTML row format (legacy) and structured data format (new)
        if (htmlRow) {
            // Legacy HTML row format
            const currentPageArea = this.getCurrentPageArea();
            if (currentPageArea === blendArea || currentPageArea === 'all') {
                const tableBody = this.getTableBodyForArea(blendArea);
                if (tableBody) {
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = htmlRow;
                    const newRow = tempDiv.firstElementChild;
                    
                    tableBody.appendChild(newRow);
                    
                    newRow.style.backgroundColor = '#ccffff';
                    setTimeout(() => {
                        newRow.style.backgroundColor = '';
                    }, 2000);
                }
            }
        } else if (data.new_blend_id) {
            // 🎯 NEW: Structured data format - use the same logic as addBlendRowToTable
            const currentPageArea = this.getCurrentPageArea();
            if (currentPageArea === blendArea || currentPageArea === 'all') {
                this.addBlendRowToTable(data);
            }
        } else {
            console.warn('⚠️ addBlend received data without html_row or structured format:', data);
        }
    }

    handleBlendMoved(data) {
        const currentPageArea = this.getCurrentPageArea();
        
        // Remove blend from old area
        const oldBlendId = data.old_blend_id;
        const oldBlendArea = data.old_blend_area;
        
        if (currentPageArea === oldBlendArea || currentPageArea === 'all') {
            const oldRow = document.querySelector(`tr[data-blend-id="${oldBlendId}"]`);
            
            if (oldRow) {
                oldRow.style.backgroundColor = '#ffdddd';
                setTimeout(() => {
                    oldRow.remove();
                }, 1000);
            } else {
                console.warn(`⚠️ Could not find old row with data-blend-id="${oldBlendId}"`);
            }
        }
        
        // Add blend to new area (only if we're viewing the destination area)
        const newBlendArea = data.new_blend_area;
        
        if (currentPageArea === newBlendArea || currentPageArea === 'all') {
            // Add the new row to the table
            this.addBlendRowToTable(data);
            
            // Create a subtle notification that blend moved here
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                padding: 8px 12px;
                color: #155724;
                font-size: 14px;
                z-index: 9999;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                transition: opacity 0.3s ease;
            `;
            notification.innerHTML = `
                <strong>Blend moved:</strong> ${data.item_code} (Lot ${data.lot_number})
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remove notification after 3 seconds
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }
    }

        addBlendRowToTable(data) {
        const tableBody = this.getTableBodyForArea(data.new_blend_area);
        
        if (!tableBody) {
            console.error(`❌ Could not find table body for area: ${data.new_blend_area}`);
            return;
        }
        
        // Check if row already exists to prevent duplicates
        const duplicateRow = tableBody.querySelector(`tr[data-blend-id="${data.new_blend_id}"]`);
        if (duplicateRow) {
            // Update the existing row's tank selection
            const existingTankSelect = duplicateRow.querySelector('.tankSelect');
            if (existingTankSelect) {
                // Handle tank assignment - null/empty means no tank selected (empty dropdown)
                if (data.tank !== undefined && data.tank !== null && data.tank !== '' && data.tank !== 'null' && data.tank !== 'None') {
                    existingTankSelect.value = data.tank;
                    
                    // Add visual confirmation that tank was preserved
                    existingTankSelect.style.backgroundColor = '#d4edda'; // Light green
                    existingTankSelect.style.transition = 'background-color 2s ease';
                    setTimeout(() => {
                        existingTankSelect.style.backgroundColor = '';
                    }, 2000);
                } else {
                    // No tank assigned - set to empty which should select the default "no selection" option
                    existingTankSelect.value = '';
                    
                    // If that doesn't work, try to find and select the first option (usually the default)
                    if (existingTankSelect.selectedIndex === -1 && existingTankSelect.options.length > 0) {
                        existingTankSelect.selectedIndex = 0;
                    }
                    
                    // Add visual confirmation that "None" was selected
                    existingTankSelect.style.backgroundColor = '#f8f9fa'; // Light gray
                    existingTankSelect.style.transition = 'background-color 2s ease';
                    setTimeout(() => {
                        existingTankSelect.style.backgroundColor = '';
                    }, 2000);
                }
            } else {
                console.warn(`⚠️ Could not find tank select dropdown in existing row`);
            }
            
            return; // Exit after updating existing row
        }
        
        // 🎯 Additional check: Look for rows with same lot number (fallback protection)
        const duplicateLotRow = tableBody.querySelector(`tr .lot-number-cell[lot-number="${data.lot_number}"]`);
        if (duplicateLotRow) {
            console.warn(`⚠️ Row with lot_number="${data.lot_number}" already exists - skipping duplicate creation`);
            return;
        }
        
        // Find an existing row to clone as a template
        const existingRow = tableBody.querySelector('tr[data-blend-id]:not([data-blend-id="' + data.new_blend_id + '"])');
        
        if (!existingRow) {
            console.error(`❌ Could not find existing row to clone for table structure`);
            return;
        }
        
        // Clone the existing row for perfect structure preservation
        const newRow = existingRow.cloneNode(true);
        newRow.setAttribute('data-blend-id', data.new_blend_id);
        
        // Update the data-blend-id attributes in all child elements
        const elementsWithDataAttr = newRow.querySelectorAll('[data-blend-id]');
        elementsWithDataAttr.forEach(el => {
            el.setAttribute('data-blend-id', data.new_blend_id);
        });
        
        // Apply row styling classes from WebSocket data
        if (data.row_classes) {
            // Clear existing classes that might conflict
            newRow.className = '';
            // Apply the classes from the server
            newRow.className = data.row_classes;
        } else {
            // Fallback: Apply essential classes based on template pattern
            const essentialClasses = ['tableBodyRow'];
            
            // Add blend area class (Desk_1, Desk_2, LET_Desk)
            essentialClasses.push(data.new_blend_area);
            
            // Try to preserve line-specific styling from original row if available
            if (existingRow && existingRow.className) {
                const lineRowMatch = existingRow.className.match(/(\w+)Row/);
                if (lineRowMatch && lineRowMatch[1] !== 'tableBody') {
                    essentialClasses.push(lineRowMatch[0]); // Add the full match (e.g., 'ProdRow')
                }
            }
            
            // Apply urgent styling if indicated
            if (data.is_urgent) {
                essentialClasses.push('priorityMessage');
            }
            
            // Apply special item styling
            if (data.item_code === "******") {
                essentialClasses.push('NOTE');
            } else if (data.item_code === "!!!!!") {
                essentialClasses.push('priorityMessage');
            }
            
            newRow.className = essentialClasses.join(' ');
        }
        
        // Update order number (first cell)
        const orderCell = newRow.querySelector('td:first-child, .orderCell');
        if (orderCell) {
            orderCell.textContent = data.order;
        }
        
        // Update item code (second cell typically)
        const itemCodeCell = newRow.querySelector('td:nth-child(2)');
        if (itemCodeCell) {
            itemCodeCell.textContent = data.item_code;
        }
        
        // Update item description 
        const descriptionCell = newRow.querySelector('td:nth-child(3)');
        if (descriptionCell) {
            descriptionCell.textContent = data.item_description;
        }
        
        // Update lot number cell
        const lotCell = newRow.querySelector('.lot-number-cell, td[lot-number]');
        if (lotCell) {
            lotCell.setAttribute('lot-number', data.lot_number);
            // Update the text content, preserving any inner structure
            const lotTextNodes = Array.from(lotCell.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
            if (lotTextNodes.length > 0) {
                lotTextNodes[0].textContent = data.lot_number;
            } else {
                // Fallback: find the text content area
                const lotTextElement = lotCell.querySelector('span, div') || lotCell;
                if (lotTextElement !== lotCell) {
                    lotTextElement.textContent = data.lot_number;
                } else {
                    lotCell.textContent = data.lot_number;
                }
            }
        }
        
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
        
        // Update blend status with proper data attributes for tooltips
        const statusSpan = newRow.querySelector('.blend-sheet-status');
        if (statusSpan) {
            statusSpan.setAttribute('data-has-been-printed', data.has_been_printed);
            statusSpan.setAttribute('data-print-history', data.print_history_json || '[]');
            statusSpan.setAttribute('data-record-id', data.new_blend_id);
            statusSpan.innerHTML = data.last_print_event_str;
            
            // Add the edited indicator if needed
            if (data.was_edited_after_last_print) {
                statusSpan.innerHTML += '<sup class="edited-after-print-indicator">!</sup>';
            }
        }
        
        // Update Short column (8th column) with hourshort value from frontend
        const shortCell = newRow.querySelector('td:nth-child(8)');
        if (shortCell) {
            // Clear existing content to prevent contamination from cloned row
            shortCell.textContent = '';
            shortCell.removeAttribute('data-hour-short');
            
            if (data.hourshort !== undefined && data.hourshort !== null) {
                // Set the data-hour-short attribute with the value from frontend
                shortCell.setAttribute('data-hour-short', parseFloat(data.hourshort).toFixed(1));
                
                // Determine what to display based on line type and item description
                let shortDisplayValue;
                
                if (data.line && data.line !== 'Prod') {
                    // For non-Prod lines, show run date
                    if (data.run_date) {
                        const runDate = new Date(data.run_date);
                        shortDisplayValue = `${(runDate.getMonth() + 1).toString().padStart(2, '0')}/${runDate.getDate().toString().padStart(2, '0')}/${runDate.getFullYear().toString().slice(-2)}`;
                    } else {
                        shortDisplayValue = 'N/A';
                    }
                } else if (data.item_description && data.item_description.includes('LET') && data.item_description.includes('(kinpak)')) {
                    // For LET kinpak items, show run date
                    if (data.run_date) {
                        const runDate = new Date(data.run_date);
                        shortDisplayValue = `${(runDate.getMonth() + 1).toString().padStart(2, '0')}/${runDate.getDate().toString().padStart(2, '0')}/${runDate.getFullYear().toString().slice(-2)}`;
                    } else {
                        shortDisplayValue = 'N/A';
                    }
                } else {
                    // For regular Prod line items, show hourshort value (from frontend)
                    shortDisplayValue = parseFloat(data.hourshort).toFixed(1);
                }
                
                shortCell.textContent = shortDisplayValue;
            } else {
                // No hourshort data provided - set a placeholder
                shortCell.textContent = 'N/A';
                console.warn(`⚠️ No hourshort data provided from frontend, set to N/A`);
            }
        } else {
            console.error(`❌ Could not find Short column (8th column) in new row`);
            // Debug: Show all cells in the row
            const allCells = newRow.querySelectorAll('td');
            console.log(`🔍 Row has ${allCells.length} cells:`, Array.from(allCells).map((cell, index) => `${index + 1}: "${cell.textContent.trim()}"`));
        }
        
        // Update any dropdown IDs to be unique
        const dropdownButtons = newRow.querySelectorAll('[id*="dropdown"], [id*="Dropdown"]');
        dropdownButtons.forEach(button => {
            const oldId = button.id;
            const newId = oldId.replace(/\d+$/, data.new_blend_id);
            button.id = newId;
            
            // Update any aria-labelledby references
            const relatedElements = newRow.querySelectorAll(`[aria-labelledby="${oldId}"]`);
            relatedElements.forEach(el => {
                el.setAttribute('aria-labelledby', newId);
            });
        });
        
                // Update tank selection dropdown
        const tankSelect = newRow.querySelector('.tankSelect');
        if (tankSelect) {
            // Clear existing selection to prevent contamination from cloned row
            tankSelect.value = '';
            
            // Handle tank assignment - null/empty means no tank selected (empty dropdown)
            if (data.tank !== undefined && data.tank !== null && data.tank !== '' && data.tank !== 'null' && data.tank !== 'None') {
                // Set the tank value from WebSocket data
                tankSelect.value = data.tank;
                
                // Add visual confirmation that tank was preserved
                tankSelect.style.backgroundColor = '#d4edda'; // Light green
                tankSelect.style.transition = 'background-color 2s ease';
                setTimeout(() => {
                    tankSelect.style.backgroundColor = '';
                }, 2000);
            } else {
                // No tank assigned - set to empty which should select the default "no selection" option
                tankSelect.value = '';
                
                // If that doesn't work, try to find and select the first option (usually the default)
                if (tankSelect.selectedIndex === -1 && tankSelect.options.length > 0) {
                    tankSelect.selectedIndex = 0;
                }
                
                // Add visual confirmation that "None" was selected
                tankSelect.style.backgroundColor = '#f8f9fa'; // Light gray
                tankSelect.style.transition = 'background-color 2s ease';
                setTimeout(() => {
                    tankSelect.style.backgroundColor = '';
                }, 2000);
            }
        } else {
            console.warn(`⚠️ Could not find tank select dropdown (.tankSelect) in new row`);
        }

        // Update management dropdown links
        const managementLinks = newRow.querySelectorAll('a[href*="schedule-management-request"]');
        managementLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href) {
                // Replace the old blend ID with the new one
                const newHref = href.replace(/\/\d+\?/, `/${data.new_blend_id}?`);
                link.setAttribute('href', newHref);
            }
        });
        
        // Find the correct position to insert the row based on order
        const existingRows = Array.from(tableBody.querySelectorAll('tr[data-blend-id]'));
        let insertPosition = existingRows.length; // Default to end
        
        for (let i = 0; i < existingRows.length; i++) {
            const existingOrderCell = existingRows[i].querySelector('td:first-child, .orderCell');
            const existingOrder = parseInt(existingOrderCell?.textContent || '999', 10);
            if (data.order < existingOrder) {
                insertPosition = i;
                break;
            }
        }
        
        // Insert the row at the correct position
        if (insertPosition >= existingRows.length) {
            tableBody.appendChild(newRow);
        } else {
            tableBody.insertBefore(newRow, existingRows[insertPosition]);
        }
        
        // Add visual feedback - blue highlight that fades to normal
        newRow.style.backgroundColor = '#cce5ff';
        newRow.style.transition = 'background-color 2s ease';
        
        setTimeout(() => {
            newRow.style.backgroundColor = '';
        }, 2000);
        
        // Initialize tooltips for the new row's status elements
        this.initializeTooltipsForRow(newRow);
        
        // 🚰 Initialize tank selection event handlers for the new row
        this.initializeTankSelectForRow(newRow);
        
        // Scroll the new row into view
        newRow.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center',
            inline: 'nearest'
        });
    }

    handleScheduleReorder(data) {
        // 🎯 PROTECTION: Skip WebSocket reorder updates during manual sorting
        if (window.isDragging || (window.blendScheduleWS && window.blendScheduleWS.isDragging)) {
            console.log("🎯 Skipping WebSocket schedule reorder - manual sort in progress");
            return;
        }
        
        const blendArea = data.blend_area;
        const reorderedItems = data.reordered_items;
        const totalReordered = data.total_reordered;
        
        const currentPageArea = this.getCurrentPageArea();
        if (currentPageArea === blendArea || currentPageArea === 'all') {
            const table = this.getTableForArea(blendArea);
            if (!table) {
                console.warn(`Could not find table for area: ${blendArea}`);
                return;
            }
            
            // Update order numbers in place
            reorderedItems.forEach(item => {
                let row = null;
                
                // Try to find row by blend_id first (for drag-and-drop updates)
                if (item.blend_id) {
                    row = table.querySelector(`tr[data-blend-id="${item.blend_id}"]`);
                }
                
                // If not found by blend_id, try to find by lot_number (for sort updates)
                if (!row && item.lot_number) {
                    // Look for lot number in the lot number cell (usually 5th column)
                    const lotCells = table.querySelectorAll('td.lot-number-cell, td[lot-number]');
                    for (let lotCell of lotCells) {
                        const lotNumber = lotCell.getAttribute('lot-number') || lotCell.textContent.trim();
                        if (lotNumber === item.lot_number) {
                            row = lotCell.closest('tr');
                            break;
                        }
                    }
                }
                
                if (row) {
                    // Update the order cell (usually first column)
                    const orderCell = row.querySelector('td:first-child');
                    if (orderCell) {
                        orderCell.textContent = item.new_order;
                        
                        // Add visual feedback for changed items
                        row.style.backgroundColor = '#fff3cd'; // Light yellow
                        setTimeout(() => {
                            row.style.backgroundColor = '';
                        }, 2000);
                    }
                } else {
                    console.warn(`⚠️ Could not find row for item:`, item);
                }
            });
            
            // Re-sort the table rows based on new order
            this.resortTableByOrder(table);
            
            // Show subtle notification
            this.showOrderUpdateNotification(totalReordered, blendArea, data.update_source);
        }
    }

    getTableForArea(blendArea) {
        const currentPageArea = this.getCurrentPageArea();
        
        if (currentPageArea === 'all') {
            // 🎯 ENHANCED: On "all schedules" page, find table within specific tab container
            let containerSelector;
            if (blendArea === 'Desk_1') {
                containerSelector = '#desk1Container #desk1ScheduleTable';
            } else if (blendArea === 'Desk_2') {
                containerSelector = '#desk2Container #desk2ScheduleTable';
            } else if (blendArea === 'LET_Desk') {
                containerSelector = '#LETDeskContainer #letDeskScheduleTable';
            } else if (blendArea === 'Hx') {
                containerSelector = '#horixContainer table';
            } else if (blendArea === 'Dm') {
                containerSelector = '#drumsContainer table';
            } else if (blendArea === 'Totes') {
                containerSelector = '#totesContainer table';
            } else {
                console.warn(`⚠️ Unknown blend area for all schedules page: ${blendArea}`);
                return null;
            }
            
            const table = document.querySelector(containerSelector);
            if (!table) {
                console.warn(`⚠️ Could not find table for ${blendArea} in all schedules page using selector: ${containerSelector}`);
            }
            return table;
        } else {
            // On individual desk pages, use the standard logic
            if (blendArea === 'Desk_1' || blendArea === 'Desk_2' || blendArea === 'LET_Desk') {
                return document.querySelector('#deskScheduleTable');
            }
            // For other areas, find the main table
            return document.querySelector('table');
        }
    }

    resortTableByOrder(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Get all rows except header
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Sort rows by order number (first cell)
        rows.sort((a, b) => {
            const orderA = parseInt(a.querySelector('td:first-child')?.textContent || '999', 10);
            const orderB = parseInt(b.querySelector('td:first-child')?.textContent || '999', 10);
            return orderA - orderB;
        });
        
        // Clear tbody and re-append in correct order
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
    }

    showOrderUpdateNotification(totalReordered, blendArea, updateSource = null) {
        // Create a subtle notification banner
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 10px 15px;
            color: #155724;
            font-weight: 500;
            z-index: 9999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        
        // Customize message based on update source
        let message = `Schedule updated: ${totalReordered} items reordered in ${blendArea}`;
        if (updateSource === 'manual_sort') {
            message = `🎯 Sort applied: ${totalReordered} items reordered in ${blendArea}`;
        }
        
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Fade out and remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    initializeTooltipsForRow(row) {
        // Find all blend-sheet-status elements in this specific row
        const statusElements = row.querySelectorAll('.blend-sheet-status');
        
        statusElements.forEach(statusSpan => {
            try {
                // Dispose of any existing tooltip to prevent conflicts
                const existingTooltip = bootstrap.Tooltip.getInstance(statusSpan);
                if (existingTooltip) {
                    existingTooltip.dispose();
                }

                const printHistoryJSON = statusSpan.getAttribute('data-print-history');
                const hasBeenPrinted = statusSpan.getAttribute('data-has-been-printed') === 'true';
                let tooltipTitle;

                // Get current user for tooltip personalization
                const rawCurrentUser = window.currentUserUsername || null;
                const currentUser = rawCurrentUser ? rawCurrentUser.trim() : null;

                if (printHistoryJSON && printHistoryJSON !== 'null' && printHistoryJSON.trim() !== '') {
                    try {
                        const printHistory = JSON.parse(printHistoryJSON);
                        if (Array.isArray(printHistory) && printHistory.length > 0) {
                            let historyHtml = '<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>';
                            printHistory.forEach(entry => {
                                const printedAt = entry.printed_at ? new Date(entry.printed_at).toLocaleString() : (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A');
                                
                                let printerDisplay = 'Unknown User';
                                const originalPrintedByUsername = entry.printed_by_username;
                                const userFromEntry = entry.user;

                                if (originalPrintedByUsername) { 
                                    const trimmedOriginalUsername = originalPrintedByUsername.trim();
                                    if (currentUser && trimmedOriginalUsername.toLowerCase() === currentUser.toLowerCase()) {
                                        printerDisplay = "(You)"; 
                                    } else {
                                        printerDisplay = trimmedOriginalUsername; 
                                    }
                                } else if (userFromEntry) {
                                    const trimmedUserFromEntry = userFromEntry.trim();
                                    if (currentUser && trimmedUserFromEntry.toLowerCase() === currentUser.toLowerCase()) {
                                        printerDisplay = "(You)";
                                    } else if (trimmedUserFromEntry === "You") {
                                        printerDisplay = "(You)"; 
                                    } else {
                                        printerDisplay = trimmedUserFromEntry;
                                    }
                                } 
                                
                                historyHtml += `<tr><td>${printerDisplay}</td><td>${printedAt}</td></tr>`;
                            });
                            historyHtml += '</tbody></table>';
                            tooltipTitle = historyHtml;

                            // Add visual indicator for multiple prints
                            if (printHistory.length > 1) {
                                statusSpan.classList.add('has-multiple-prints');
                            } else {
                                statusSpan.classList.remove('has-multiple-prints');
                            }
                        } else if (hasBeenPrinted) {
                            tooltipTitle = 'Printed (detailed history unavailable).';
                            statusSpan.classList.remove('has-multiple-prints');
                        } else {
                            tooltipTitle = 'Blend sheet has not been printed.';
                            statusSpan.classList.remove('has-multiple-prints');
                        }
                    } catch (e) {
                        console.error("Error parsing print history JSON:", e, printHistoryJSON);
                        tooltipTitle = "Error loading print history.";
                        statusSpan.classList.remove('has-multiple-prints');
                    }
                } else if (hasBeenPrinted) {
                    tooltipTitle = 'Printed (detailed history unavailable).';
                    statusSpan.classList.remove('has-multiple-prints');
                } else {
                    tooltipTitle = 'Blend sheet has not been printed.';
                    statusSpan.classList.remove('has-multiple-prints');
                }

                if (tooltipTitle) {
                    // Create new Bootstrap tooltip with the same configuration as the main page
                    const newTooltip = new bootstrap.Tooltip(statusSpan, {
                        title: tooltipTitle,
                        html: true,
                        sanitize: false,
                        trigger: 'hover focus',
                        placement: 'top',
                        boundary: 'scrollParent',
                        customClass: 'print-history-tooltip',
                        container: 'body'
                    });
                    
                    // Update the data attribute for Bootstrap's internal tracking
                    statusSpan.setAttribute('data-bs-original-title', tooltipTitle);
                } else {
                    console.warn(`⚠️ No tooltip title generated for status element`);
                }
            } catch (error) {
                console.error(`❌ Error initializing tooltip for status element:`, error);
            }
        });
    }

    initializeTooltipForElement(statusSpan) {
        try {
            // Dispose of any existing tooltip to prevent conflicts
            const existingTooltip = bootstrap.Tooltip.getInstance(statusSpan);
            if (existingTooltip) {
                existingTooltip.dispose();
            }

            const printHistoryJSON = statusSpan.getAttribute('data-print-history');
            const hasBeenPrinted = statusSpan.getAttribute('data-has-been-printed') === 'true';
            let tooltipTitle;

            // Get current user for tooltip personalization
            const rawCurrentUser = window.currentUserUsername || null;
            const currentUser = rawCurrentUser ? rawCurrentUser.trim() : null;

            if (printHistoryJSON && printHistoryJSON !== 'null' && printHistoryJSON.trim() !== '') {
                try {
                    const printHistory = JSON.parse(printHistoryJSON);
                    if (Array.isArray(printHistory) && printHistory.length > 0) {
                        let historyHtml = '<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>';
                        printHistory.forEach(entry => {
                            const printedAt = entry.printed_at ? new Date(entry.printed_at).toLocaleString() : (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A');
                            
                            let printerDisplay = 'Unknown User';
                            const originalPrintedByUsername = entry.printed_by_username;
                            const userFromEntry = entry.user;

                            if (originalPrintedByUsername) { 
                                const trimmedOriginalUsername = originalPrintedByUsername.trim();
                                if (currentUser && trimmedOriginalUsername.toLowerCase() === currentUser.toLowerCase()) {
                                    printerDisplay = "(You)"; 
                                } else {
                                    printerDisplay = trimmedOriginalUsername; 
                                }
                            } else if (userFromEntry) {
                                const trimmedUserFromEntry = userFromEntry.trim();
                                if (currentUser && trimmedUserFromEntry.toLowerCase() === currentUser.toLowerCase()) {
                                    printerDisplay = "(You)";
                                } else if (trimmedUserFromEntry === "You") {
                                    printerDisplay = "(You)"; 
                                } else {
                                    printerDisplay = trimmedUserFromEntry;
                                }
                            } 
                            
                            historyHtml += `<tr><td>${printerDisplay}</td><td>${printedAt}</td></tr>`;
                        });
                        historyHtml += '</tbody></table>';
                        tooltipTitle = historyHtml;

                        // Add visual indicator for multiple prints
                        if (printHistory.length > 1) {
                            statusSpan.classList.add('has-multiple-prints');
                        } else {
                            statusSpan.classList.remove('has-multiple-prints');
                        }
                    } else if (hasBeenPrinted) {
                        tooltipTitle = 'Printed (detailed history unavailable).';
                        statusSpan.classList.remove('has-multiple-prints');
                    } else {
                        tooltipTitle = 'Blend sheet has not been printed.';
                        statusSpan.classList.remove('has-multiple-prints');
                    }
                } catch (e) {
                    console.error("Error parsing print history JSON:", e, printHistoryJSON);
                    tooltipTitle = "Error loading print history.";
                    statusSpan.classList.remove('has-multiple-prints');
                }
            } else if (hasBeenPrinted) {
                tooltipTitle = 'Printed (detailed history unavailable).';
                statusSpan.classList.remove('has-multiple-prints');
            } else {
                tooltipTitle = 'Blend sheet has not been printed.';
                statusSpan.classList.remove('has-multiple-prints');
            }

            if (tooltipTitle) {
                // Create new Bootstrap tooltip with the same configuration as the main page
                const newTooltip = new bootstrap.Tooltip(statusSpan, {
                    title: tooltipTitle,
                    html: true,
                    sanitize: false,
                    trigger: 'hover focus',
                    placement: 'top',
                    boundary: 'scrollParent',
                    customClass: 'print-history-tooltip',
                    container: 'body'
                });
                
                // Update the data attribute for Bootstrap's internal tracking
                statusSpan.setAttribute('data-bs-original-title', tooltipTitle);
            } else {
                console.warn(`⚠️ No tooltip title generated for single status element`);
            }
        } catch (error) {
            console.error(`❌ Error initializing tooltip for single status element:`, error);
        }
    }

    initializeTankSelectForRow(row) {
        try {
            const tankSelect = row.querySelector('.tankSelect');
            if (!tankSelect) {
                console.warn(`⚠️ No tank select dropdown found in row`);
                return;
            }
            
            // Remove any existing event handlers to prevent duplicates
            $(tankSelect).off('change.websocket focus.websocket');
            
            // Add change event handler with namespace for easy removal
            $(tankSelect).on('change.websocket', function() {
                const $this = $(this);
                const $row = $this.closest('tr');
                
                // Use data-blend-id for reliable identification
                const blendId = $row.attr('data-blend-id');
                const lotNumber = $row.find('.lot-number-cell').attr('lot-number') || $row.find('td:eq(4)').text().trim();
                const tank = $this.val();
                const blendArea = new URL(window.location.href).searchParams.get("blend-area");
                
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
                        // Clear visual feedback on success
                        setTimeout(() => {
                            $this.css('backgroundColor', '');
                        }, 1000);
                    },
                    error: function(xhr, status, error) {
                        console.error(`❌ Tank update failed (WebSocket row):`, error);
                        
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
            
            // Add focus event handler to store previous value for error recovery
            $(tankSelect).on('focus.websocket', function() {
                $(this).data('previous-value', $(this).val());
            });
            
        } catch (error) {
            console.error(`❌ Error initializing tank selection for row:`, error);
        }
    }

    getCurrentPageArea() {
        const url = window.location.href;
        
        if (url.includes('blend-area=Desk_1')) {
            return 'Desk_1';
        }
        if (url.includes('blend-area=Desk_2')) {
            return 'Desk_2';
        }
        if (url.includes('blend-area=LET_Desk')) {
            return 'LET_Desk';
        }
        if (url.includes('blend-area=Hx')) {
            return 'Hx';
        }
        if (url.includes('blend-area=Dm')) {
            return 'Dm';
        }
        if (url.includes('blend-area=Totes')) {
            return 'Totes';
        }
        if (url.includes('blend-area=Pails')) {
            return 'Pails';
        }
        if (url.includes('blend-area=all')) {
            return 'all';
        }
        
        // Enhanced fallback detection
        if (url.includes('/drumschedule') || url.includes('drum')) {
            return 'Dm';
        }
        if (url.includes('/horixschedule') || url.includes('horix')) {
            return 'Hx';
        }
        if (url.includes('/deskoneschedule') || url.includes('desk') && url.includes('one')) {
            return 'Desk_1';
        }
        if (url.includes('/desktwoschedule') || url.includes('desk') && url.includes('two')) {
            return 'Desk_2';
        }
        if (url.includes('/toteschedule') || url.includes('tote')) {
            return 'Totes';
        }
        if (url.includes('/allschedules') || url.includes('all')) {
            return 'all';
        }
        
        return 'all';
    }

    getTableBodyForArea(blendArea) {
        const currentPageArea = this.getCurrentPageArea();
        
        if (currentPageArea === 'all') {
            // 🎯 ENHANCED: On "all schedules" page, find table within specific tab container
            let containerSelector;
            if (blendArea === 'Desk_1') {
                containerSelector = '#desk1Container #desk1ScheduleTable tbody';
            } else if (blendArea === 'Desk_2') {
                containerSelector = '#desk2Container #desk2ScheduleTable tbody';
            } else if (blendArea === 'LET_Desk') {
                containerSelector = '#LETDeskContainer #letDeskScheduleTable tbody';
            } else if (blendArea === 'Hx') {
                containerSelector = '#horixContainer table tbody';
            } else if (blendArea === 'Dm') {
                containerSelector = '#drumsContainer table tbody';
            } else if (blendArea === 'Totes') {
                containerSelector = '#totesContainer table tbody';
            } else {
                console.warn(`⚠️ Unknown blend area for all schedules page: ${blendArea}`);
                return null;
            }
            
            const tableBody = document.querySelector(containerSelector);
            if (!tableBody) {
                console.warn(`⚠️ Could not find table body for ${blendArea} in all schedules page using selector: ${containerSelector}`);
            }
            return tableBody;
        } else {
            // On individual desk pages, use the standard logic
            if (blendArea === 'Desk_1' || blendArea === 'Desk_2' || blendArea === 'LET_Desk') {
                return document.querySelector('#deskScheduleTable tbody');
            }
            return document.querySelector('table tbody');
        }
    }

    startPing() {
        this.pingInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({
                    action: 'ping',
                    timestamp: Date.now()
                }));
            }
        }, 30000);
    }

    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error("Max reconnection attempts reached");
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), 10000);
        
        setTimeout(() => {
            this.initWebSocket();
        }, delay);
    }
}