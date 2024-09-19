import { getContainersFromCount, getURLParameter } from '../requestFunctions/requestFunctions.js'

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
    constructor(listId) {
        try {
            this.socket = new WebSocket(`ws://${window.location.host}/ws/count_list/${listId}/`);
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
            this.socket = new WebSocket(this.socket.url);
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
        $(`p[data-countrecord-id="${recordId}"]`).text(newOnHand);
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
    }
}

export class CountCollectionWebSocket {
    constructor() {
        this.socket = new WebSocket(`ws://${window.location.host}/ws/count_collection/`);
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
            this.socket = new WebSocket(this.socket.url);
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