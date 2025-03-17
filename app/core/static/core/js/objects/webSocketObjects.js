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

    updateCount(recordId, recordType, recordInformation) {
        try {
            this.socket.send(JSON.stringify({
                action: 'update_count',
                record_id: recordId,
                counted_quantity: recordInformation['counted_quantity'],
                expected_quantity: recordInformation['expected_quantity'],
                variance: recordInformation['variance'],
                counted_date: recordInformation['counted_date'],
                counted: recordInformation['counted'],
                comment: recordInformation['comment'],
                location: recordInformation['location'],
                containers: recordInformation['containers'],
                containerId: recordInformation['containerId'],
                record_type: recordType
            }));
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
        // let populateContainerFields = this.populateContainerFields
        console.log(`updated countlist ui: ${data}`);
        $(`input[data-countrecord-id="${recordId}"].counted_quantity`).val(data['data']['counted_quantity']);
        $(`span[data-countrecord-id="${recordId}"].expected-quantity-span`).text(data['data']['expected_quantity']);
        $(`td[data-countrecord-id="${recordId}"].tbl-cell-variance`).text(data['data']['variance']);
        $(`td[data-countrecord-id="${recordId}"].tbl-cell-counted_date`).text(data['data']['counted_date']);
        $(`textarea[data-countrecord-id="${recordId}"].comment`).val(data['data']['comment']);
        $(`select[data-countrecord-id="${recordId}"].location-selector`).val(data['data']['location']);
        const checkbox = $(`input[data-countrecord-id="${recordId}"].counted-input`);
        checkbox.prop("checked", data['data']['counted']);
        if (data['data']['counted']) {
            checkbox.parent().removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
        } else {
            checkbox.parent().removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
        }
        $(`div[data-countrecord-id="${data['data']['record_id']}"].container-monitor`).attr('data-container-id-updated', data['data']['containerId']);
        // populateContainerFields(recordId, data['data']['containers'], data['data']['containerId']);
    }

    updateOnHandUI(recordId, newOnHand) {
        $(`span[data-countrecord-id="${recordId}"]`).text(parseFloat(newOnHand).toFixed(4));
    }

    deleteCountFromUI(recordId) {
        $(`tr[data-countrecord-id="${recordId}"]`).remove()
    }

    addCountRecordToUI(recordId, data) {
        $("#addCountListItemModal").modal('hide'); // Correct method to hide the modal
        const rows = document.querySelectorAll('#countsTable tr.countRow');
        const secondToLastRow = rows[rows.length - 1];
        const newRow = secondToLastRow.cloneNode(true);
        $(newRow).attr('data-countrecord-id', recordId);
        $(newRow).find('td input select textarea span div button').each(function() {
            $(this).attr('data-countrecord-id', recordId);
        });
        
        // Also update any container tables and their children
        $(newRow).find('table[data-countrecord-id]').attr('data-countrecord-id', recordId);
        $(newRow).find('tbody[data-countrecord-id]').attr('data-countrecord-id', recordId);
        $(newRow).find('a.itemCodeDropdownLink').text(data['item_code']);
        $(newRow).find('td.tbl-cell-item_description').text(data['item_description']);
        $(newRow).find('input.counted_quantity').val(data['counted_quantity']);
        $(newRow).find('span.expected-quantity-span').text(data['expected_quantity']);
        $(newRow).find('td.tbl-cell-variance').text(data['variance']);
        $(newRow).find('td.tbl-cell-counted_date').text(data['counted_date']);
        $(newRow).find('textarea.comment').val(data['comment']);
        $(newRow).find('select.location-selector').val(data['location']);
        const checkbox = $(newRow).find('input.counted-input');
        checkbox.prop("checked", data['counted']);
        if (data['counted']) {
            checkbox.parent().removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
        } else {
            checkbox.parent().removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
        };
        $(secondToLastRow).after(newRow);
        
        try {
            // Hide modal if open
            if ($('#addCountListItemModal').hasClass('show')) {
                $('#addCountListItemModal').modal('hide');
            }
            
            // Check if table exists before proceeding
            this._checkTableStructure('BEFORE');
            
            // Method 1: Try using the primary approach - clone an existing row
            console.log("🔍 ATTEMPT 1: Using row cloning approach");
            
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
                console.log("🔄 Found existing row to use as template");
                const success = this._createRowByCloning(existingRow, recordId, data, tbody);
                
                if (success) {
                    console.log("✅ Row successfully created by cloning");
                    
                    // Bind to ContainerManager if it exists
                    if (typeof ContainerManager !== 'undefined') {
                        console.log(`Binding row ${recordId} to ContainerManager`);
                        ContainerManager.renderContainerRows(recordId);
                    } else {
                        console.log("ContainerManager not found, cannot bind containers");
                    }
                    
                    // Set a timeout to check if the row is actually visible after insertion
                    setTimeout(() => this._checkTableStructure('AFTER', recordId), 1000);
                    return true;
                }
            }
            
            // Method 2: Try using the direct HTML creation approach
            console.log("🔍 ATTEMPT 2: Using direct HTML creation approach");
            const directInsertSuccess = this._emergencyDirectRowInsertion(recordId, data);
            
            if (directInsertSuccess) {
                console.log("✅ Row successfully created using direct HTML insertion");
                
                // Bind to ContainerManager if it exists
                if (typeof ContainerManager !== 'undefined') {
                    console.log(`Binding row ${recordId} to ContainerManager`);
                    ContainerManager.renderContainerRows(recordId);
                } else {
                    console.log("ContainerManager not found, cannot bind containers");
                }
                
                // Set a timeout to check if the row is actually visible after insertion
                setTimeout(() => this._checkTableStructure('AFTER', recordId), 1000);
                return true;
            }
            
            // If all else fails, try refreshing the table
            console.log("⚠️ All insertion attempts failed, attempting to refresh table");
            if (typeof window.debugRefreshTable === 'function') {
                window.debugRefreshTable();
            }
            
            return false;
        } catch (error) {
            console.error("Error adding count record to UI:", error);
            return false;
        }
    }
    
    _createDirectRow(recordId, data, tbody, addItemRow) {
        console.log(`🔥 Creating row through direct DOM manipulation for ID ${recordId}`);
        
        // Create the main row
        const tr = document.createElement('tr');
        tr.setAttribute('data-countrecord-id', recordId);
        tr.className = 'countRow';
        
        // Get the record type
        const recordType = getURLParameter('recordType');
        
        // Get existing location options from another selector if available
        let locationOptionsHtml = '';
        const existingSelector = document.querySelector('select.location-selector');
        if (existingSelector) {
            locationOptionsHtml = Array.from(existingSelector.options)
                .map(opt => `<option value="${opt.value}" ${opt.value === data.location ? 'selected' : ''}>${opt.text}</option>`)
                .join('');
        } else {
            locationOptionsHtml = `<option value="${data.location || ''}" selected>${data.location || ''}</option>`;
        }
        
        // Build full HTML for the row (simplified from template version but with all essential elements)
        tr.innerHTML = `
            <td data-countrecord-id="${recordId}" class="tbl-cell-item_code text-right">
                <div class="dropdown">
                    <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown">${data.item_code}</a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item partialContainerLabelLink" data-itemcode="${data.item_code}">Partial Container Label</a></li>
                    </ul>
                </div>
            </td>
            <td data-countrecord-id="${recordId}" class="tbl-cell-item_description">${data.item_description}</td>
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
                <i class="fa fa-trash discardButton" data-countrecord-id="${recordId}" data-countlist-id="${getURLParameter('listId')}" aria-hidden="true"></i>
            </td>
        `;
        
        // Insert at the right position
        if (addItemRow) {
            tbody.insertBefore(tr, addItemRow);
        } else {
            tbody.appendChild(tr);
        }
        
        // Copy event handlers from existing rows if possible
        const existingRow = tbody.querySelector('tr.countRow:not([data-countrecord-id="' + recordId + '"])');
        if (existingRow) {
            this._copyEventHandlers(existingRow, tr);
        }
        
        // Highlight the new row
        $(tr).css('background-color', '#ffffcc').animate({
            backgroundColor: 'transparent'
        }, 2000);
        
        console.log(`✅ Successfully created row through direct DOM manipulation`);
        return tr;
    }
    
    _copyEventHandlers(sourceRow, targetRow) {
        // Try to copy click handlers from buttons and inputs
        try {
            // For each button type in the source, find equivalent in target and copy click handlers
            $(sourceRow).find('button, input, select, i.fa').each(function() {
                const className = this.className;
                const targetElement = $(targetRow).find(this.tagName + '.' + className.split(' ')[0]);
                
                if (targetElement.length) {
                    const events = $._data(this, 'events');
                    if (events && events.click) {
                        events.click.forEach(event => {
                            targetElement.on('click', event.handler);
                        });
                    }
                }
            });
        } catch (e) {
            console.warn("Could not copy all event handlers", e);
        }
    }

    _emergencyDirectRowInsertion(recordId, data) {
        try {
            console.log("🧿 Attempting emergency row insertion with Bootstrap reinitialization");
            
            // Get the table directly from the DOM
            const table = document.getElementById('countsTable');
            if (!table) {
                console.error("Cannot find table for emergency insertion");
                return false;
            }
            
            // Find the table body
            const tbody = table.querySelector('tbody');
            if (!tbody) {
                console.error("Cannot find tbody for emergency insertion");
                return false;
            }
            
            // Look for an existing row to clone as a template
            const existingRow = tbody.querySelector('tr.countRow');
            if (existingRow) {
                console.log("🔄 Found existing row to use as template - using clone approach");
                return this._createRowByCloning(existingRow, recordId, data, tbody);
            }
            
            // Fallback to direct creation if no template row found
            console.log("⚠️ No template row found - using direct creation approach");
            
            // Create a simple row with basic content
            const row = document.createElement('tr');
            row.setAttribute('data-countrecord-id', recordId);
            row.className = 'countRow';
            
            // Get the record type
            const recordType = getURLParameter('recordType');
            
            // Get existing location options from another selector if available
            let locationOptionsHtml = '';
            const existingSelector = document.querySelector('select.location-selector');
            if (existingSelector) {
                locationOptionsHtml = Array.from(existingSelector.options)
                    .map(opt => `<option value="${opt.value}" ${opt.value === data.location ? 'selected' : ''}>${opt.text}</option>`)
                    .join('');
            } else {
                locationOptionsHtml = `<option value="${data.location || ''}" selected>${data.location || ''}</option>`;
            }
            
            // Extract the existing HTML structure directly from the page to ensure consistent markup
            const isCounted = data.counted ? 'checked' : '';
            const countedCellClass = data.counted ? 'checkedcountedcell' : 'uncheckedcountedcell';
            
            // Build full HTML for the row - using the EXACT structure from the template
            row.innerHTML = `
                <td data-countrecord-id="${recordId}" class="tbl-cell-item_code text-right">
                    <div class="dropdown">
                        <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown" readonly="readonly">${data.item_code}</a>
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
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted_date noPrint" readonly>${data.counted_date || ''}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-variance text-right noPrint">${parseFloat(data.variance || 0).toFixed(0)}</td>
                <td data-countrecord-id="${recordId}" class="tbl-cell-counted text-center noPrint ${countedCellClass}">
                    <input data-countrecord-id="${recordId}" class="counted-input" type="checkbox" ${isCounted}>
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
                    <i class="fa fa-trash discardButton" data-countrecord-id="${recordId}" data-countlist-id="${getURLParameter('listId')}" aria-hidden="true"></i>
                </td>
            `;
            
            // Find the "Add Item" row if it exists
            const addItemRow = Array.from(tbody.querySelectorAll('tr')).find(row => 
                row.querySelector('button[data-bs-target="#addCountListItemModal"]') || 
                row.querySelector('#modalToggle')
            );
            
            // Insert before add item row or at the end
            if (addItemRow) {
                tbody.insertBefore(row, addItemRow);
                console.log("Row inserted before Add Item row");
            } else {
                tbody.appendChild(row);
                console.log("Row appended to end of table");
            }
            
            // Highlight the new row to make it more visible on insert
            $(row).css({
                'backgroundColor': '#ffffcc',
                'transition': 'background-color 2s'
            });
            
            setTimeout(() => {
                $(row).css('backgroundColor', '');
                
                // CRITICAL: Triple check modal bindings are correct
                this._ensureProperModalBindings(row, recordId);
                
                // Reinitialize Bootstrap components on the new row
                this._reinitializeBootstrap(row);
                
                // Copy event handlers from other rows
                this._copyAllEventHandlers(tbody, row, recordId);
                
                // Log success and scroll to make visible
                console.log(`✅ Row created with ID ${recordId} - initializing Bootstrap components`);
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
            
            return true;
        } catch (error) {
            console.error("Emergency insertion failed:", error);
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
                console.log("Cloned row inserted before Add Item row");
            } else {
                tbody.appendChild(newRow);
                console.log("Cloned row appended to end of table");
            }
            
            // Highlight the new row
            $(newRow).css({
                'backgroundColor': '#ffffcc',
                'transition': 'background-color 2s'
            });
            
            setTimeout(() => {
                $(newRow).css('backgroundColor', '');
                
                // CRITICAL: Ensure modal bindings are correct before reinitializing
                this._ensureProperModalBindings(newRow, recordId);
                
                // Reinitialize Bootstrap components on the new row
                this._reinitializeBootstrap(newRow);
                
                // Copy event handlers from other rows
                this._copyAllEventHandlers(tbody, newRow, recordId);
                
                // Log success and scroll to make visible
                console.log(`✅ Row cloned with ID ${recordId} - all structures preserved`);
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
            
            console.log("Bootstrap components reinitialized on row");
        } catch (error) {
            console.warn("Bootstrap reinitialization failed:", error);
        }
    }
    
    _ensureProperModalBindings(row, recordId) {
        try {
            console.log(`🔮 PERFORMING EXTREME MODAL UNBINDING RITUAL FOR ROW ${recordId}`);
            
            // STEP 1: Find all modals in the document that might conflict with our new one
            const allModals = document.querySelectorAll('.modal');
            console.log(`Found ${allModals.length} total modals in document`);
            
            // STEP 2: Get our target modal and container button
            const containerCell = row.querySelector('.tbl-cell-containers');
            if (!containerCell) {
                console.error("Cannot find container cell in row");
                return;
            }
            
            const containerButton = containerCell.querySelector('button.containers');
            if (!containerButton) {
                console.error("Cannot find container button in row");
                return;
            }
            
            const modal = containerCell.querySelector('.modal');
            if (!modal) {
                console.error("Cannot find modal in container cell");
                return;
            }
            
            // STEP 3: Force-detach the modal from the DOM to break any existing bindings
            const modalParent = modal.parentNode;
            const modalNextSibling = modal.nextSibling;
            
            // Remove the modal from DOM temporarily
            modalParent.removeChild(modal);
            
            // STEP 4: Ensure the modal has a completely unique ID
            const uniqueModalId = `containersModal${recordId}_${Date.now()}`;
            modal.id = uniqueModalId;
            console.log(`🧙‍♂️ Assigned guaranteed unique ID to modal: ${uniqueModalId}`);
            
            // STEP 5: Update all references to the modal ID within the modal itself
            const modalTitle = modal.querySelector('.modal-title');
            if (modalTitle) {
                modalTitle.id = `${uniqueModalId}Label`;
            }
            
            // Find and update any buttons that target this modal
            Array.from(modal.querySelectorAll('[data-bs-dismiss="modal"]')).forEach(button => {
                button.setAttribute('data-bs-target', `#${uniqueModalId}`);
            });
            
            // STEP 6: Update all references to the modal from outside
            // First, the container button
            containerButton.setAttribute('data-bs-target', `#${uniqueModalId}`);
            
            // Then, the counted quantity input
            const countedQtyInput = row.querySelector('.counted_quantity');
            if (countedQtyInput) {
                countedQtyInput.setAttribute('data-bs-target', `#${uniqueModalId}`);
            }
            
            // STEP 7: Reinject the modified modal into the DOM
            modalParent.insertBefore(modal, modalNextSibling);
            console.log(`🔀 Modal reattached to DOM with unique ID: ${uniqueModalId}`);
            
            // STEP 8: Force destroy and recreate any Bootstrap modal objects
            if (window.bootstrap && window.bootstrap.Modal) {
                // Check if there's already a Bootstrap modal instance and destroy it
                const existingModalObj = bootstrap.Modal.getInstance(modal);
                if (existingModalObj) {
                    existingModalObj.dispose();
                    console.log(`🗑️ Disposed existing Bootstrap modal instance`);
                }
                
                // Create a new Bootstrap modal instance with up-to-date bindings
                const newModalObj = new bootstrap.Modal(modal, {
                    backdrop: true,
                    keyboard: true,
                    focus: true
                });
                console.log(`✨ Created new Bootstrap modal instance`);
                
                // Add a direct click handler to the button to force the correct modal to open
                containerButton.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`🖱️ Container button clicked, manually opening modal ${uniqueModalId}`);
                    
                    // Hide any other modals that might be open
                    Array.from(document.querySelectorAll('.modal.show')).forEach(openModal => {
                        if (openModal !== modal) {
                            const openModalInstance = bootstrap.Modal.getInstance(openModal);
                            if (openModalInstance) openModalInstance.hide();
                        }
                    });
                    
                    // Show our modal
                    newModalObj.show();
                    return false;
                };
                
                // Also update the counted quantity input to open the same modal
                if (countedQtyInput) {
                    countedQtyInput.onclick = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        newModalObj.show();
                        return false;
                    };
                }
            }
            
            console.log(`🎭 Modal binding ritual completed for row ${recordId}`);
            return true;
        } catch (error) {
            console.error("💥 Error during modal binding ritual:", error);
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
            
            console.log("Event handlers copied from existing row");
        } catch (error) {
            console.warn("Event handler copying failed:", error);
        }
    }

    _checkTableStructure(phase, newRowId = null) {
        try {
            console.group(`🔍 ${phase} INSERTION - Table Structure Check`);
            
            const table = document.getElementById('countsTable');
            if (!table) {
                console.error('Cannot find countsTable element!');
                console.groupEnd();
                return;
            }
            
            const tbody = table.querySelector('tbody');
            if (!tbody) {
                console.error('Cannot find table body!');
                console.groupEnd();
                return;
            }
            
            const rows = tbody.querySelectorAll('tr');
            console.log(`Table has ${rows.length} total rows`);
            
            // Look for Add Item row
            const addItemRow = Array.from(rows).find(row => 
                row.querySelector('button[data-bs-target="#addCountListItemModal"]') || 
                row.querySelector('#modalToggle')
            );
            
            if (addItemRow) {
                console.log(`Found Add Item row at position ${Array.from(rows).indexOf(addItemRow) + 1}`);
            } else {
                console.warn('No Add Item row found in table!');
            }
            
            // Check for the new row if in AFTER phase
            if (phase === 'AFTER' && newRowId) {
                const newRow = tbody.querySelector(`tr[data-countrecord-id="${newRowId}"]`);
                if (newRow) {
                    console.log(`✅ Found new row with ID ${newRowId} at position ${Array.from(rows).indexOf(newRow) + 1}`);
                    
                    // Check row visibility
                    const rowStyle = window.getComputedStyle(newRow);
                    console.log(`Row visibility: display=${rowStyle.display}, visibility=${rowStyle.visibility}`);
                    
                    // Check if any parent elements might be hiding it
                    let parent = newRow.parentElement;
                    while (parent && parent !== document.body) {
                        const parentStyle = window.getComputedStyle(parent);
                        if (parentStyle.display === 'none' || parentStyle.visibility === 'hidden' || parseFloat(parentStyle.opacity) === 0) {
                            console.error(`Found hidden parent element:`, parent);
                        }
                        parent = parent.parentElement;
                    }
                } else {
                    console.error(`❌ New row with ID ${newRowId} NOT FOUND in DOM!`);
                }
            }
            
            console.groupEnd();
        } catch (e) {
            console.error('Error in table structure check:', e);
            console.groupEnd();
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