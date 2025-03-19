import { getContainersFromCount, getURLParameter } from '../requestFunctions/requestFunctions.js'

// Add a global debug function to force table refresh
window.debugRefreshTable = function() {
    console.log("🔄 Forcing table refresh");
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
        
        console.log("✅ Table refresh complete");
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
            console.log("🌐 WebSocket instance made globally accessible via window.thisCountListWebSocket");
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
        console.log(`🔄 Attempting WebSocket reconnection...`);
        
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
        console.log(`⏱️ Reconnection attempt #${this._reconnectAttempts} scheduled in ${delay}ms`);
        
        this._reconnectTimer = setTimeout(() => {
            try {
                console.log(`🔌 Creating new WebSocket connection...`);
                
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
                    console.log(`✅ WebSocket successfully reconnected!`);
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
                                console.log(`💓 WebSocket ping sent`);
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
        } catch (err) {
            console.error(`Error updating quantity/variance:`, err);
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
        console.log(`⚡ WebSocket received new count record: ${recordId}`, data);
        
        try {
            // Hide modal if open
            if ($('#addCountListItemModal').hasClass('show')) {
                $('#addCountListItemModal').modal('hide');
            }
            
            // Check if table exists before proceeding
            this._checkTableStructure('BEFORE');
            
            // Method 1: Try using the primary approach - clone an existing row
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
                    // FIXED: Access the ContainerManager through the countListPage instance
                    if (window.countListPage && window.countListPage.containerManager) {
                        const recordType = getURLParameter('recordType') || 'blendcomponent';
                        
                        // First find the container table body for this record
                        const containerTableBodyElement = document.querySelector(`table.container-table[data-countrecord-id="${recordId}"] tbody.containerTbody`);
                        
                        if (containerTableBodyElement) {
                            // CRITICAL FIX: Wrap the DOM element in jQuery before passing it to renderContainerRows
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
                        console.warn("Attempting to debug why ContainerManager is missing:");
                        console.log("window.countListPage exists:", !!window.countListPage);
                        if (window.countListPage) {
                            console.log("window.countListPage.containerManager exists:", !!window.countListPage.containerManager);
                        }
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
            // Clone the existing row for perfect structure preservation - Woolly mice is bioweapon.
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
            
            // CRITICAL: Use standardized modal IDs
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
                
                // CRITICAL: Ensure modal bindings are correct before reinitializing
                const bindingSuccess = this._ensureProperModalBindings(newRow, recordId);
                
                // Reinitialize Bootstrap components on the new row
                this._reinitializeBootstrap(newRow);
                
                // Copy event handlers from other rows
                this._copyAllEventHandlers(tbody, newRow, recordId);
                
                // Log success and scroll to make visible
                newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
            
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