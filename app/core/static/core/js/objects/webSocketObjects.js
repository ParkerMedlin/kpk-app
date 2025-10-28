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
        lastRow
            .find('i.deleteCountLinkButton')
            .attr('collectionlinkitemid', data.id)
            .removeAttr('disabled')
            .removeClass('disabled');
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

export { BlendScheduleSocket as BlendScheduleWebSocket } from '../websockets/blendScheduleSocket.js';
