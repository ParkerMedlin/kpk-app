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
    constructor(options = {}) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.callbacks = {
            collection_updated: options.onCollectionUpdated,
            collection_hidden: options.onCollectionHidden || options.onCollectionDeleted,
            collection_restored: options.onCollectionRestored,
            collection_deleted: options.onCollectionDeleted,
            collection_added: options.onCollectionAdded,
            collection_order_updated: options.onCollectionOrderUpdated,
            initial_state: options.onInitialState,
            initial_state_error: options.onInitialStateError,
            message: options.onMessage,
            open: options.onOpen,
            close: options.onClose,
            error: options.onError,
            reconnect: options.onReconnect,
        };
        this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/count_collection/`);
        this.initEventListeners();
    }

    _emit(eventName, payload) {
        if (!eventName) {
            return;
        }
        const handler = this.callbacks?.[eventName];
        if (typeof handler !== 'function') {
            return;
        }
        try {
            handler(payload);
        } catch (error) {
            console.error(`CountCollectionWebSocket handler for "${eventName}" threw an error:`, error);
        }
    }

    _emitMessage(payload) {
        const handler = this.callbacks?.message;
        if (typeof handler !== 'function') {
            return;
        }
        try {
            handler(payload);
        } catch (error) {
            console.error('CountCollectionWebSocket message handler threw an error:', error);
        }
    }

    initEventListeners() {
        this.socket.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (error) {
                console.error('Failed to parse count collection WebSocket message:', error, event.data);
                return;
            }
            console.log(data);
            console.log(data.type);
            
            if (data.type === 'collection_updated') {
                this.updateCollectionUI(data.collection_id, data.new_name);
            } else if (data.type === 'collection_hidden') {
                this.removeCollectionUI(data.collection_id);
            } else if (data.type === 'collection_deleted') {
                this.removeCollectionUI(data.collection_id);
            } else if (data.type === 'collection_restored') {
                this.addCollectionUI(data);
            } else if (data.type === 'collection_added') { 
                this.addCollectionUI(data);
            } else if (data.type === 'collection_order_updated') {
                this.updateCollectionOrderUI(data.updated_order);
            } else if (data.type === 'initial_state' || data.type === 'initial_state_error') {
                // Initial state messages do not have default UI handling here.
            }

            if (data && data.type) {
                this._emit(data.type, data);
            }
            this._emitMessage(data);
        };

        this.socket.onclose = () => {
            console.error('Count collection socket closed unexpectedly');
            updateConnectionStatus('disconnected');
            this.reconnect();
            this._emit('close', { reason: 'unexpected' });
        };

        this.socket.onopen = () => {
            console.log("Count collection update WebSocket connection established.");
            this.reconnectAttempts = 0;
            updateConnectionStatus('connected');
            this._emit('open', {});
        };

        this.socket.onerror = (error) => {
            console.error('Count collection update WebSocket error:', error);
            updateConnectionStatus('disconnected');
            this._emit('error', { error });
        };

    }

    reconnect() {
        this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
        setTimeout(() => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = new URL(this.socket.url);
            url.protocol = protocol;
            this.socket = new WebSocket(url.toString());
            this.initEventListeners();
            this.socket.onopen = () => {
                updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
                this._emit('open', {});
            };
        }, 1000);
        this._emit('reconnect', { attempt: this.reconnectAttempts });
    }

    updateCollection(collectionId, newName) {
        this.socket.send(JSON.stringify({
            action: 'update_collection',
            collection_id: collectionId,
            new_name: newName
        }));
    }

    hideCollection(collectionId) {
        this.socket.send(JSON.stringify({
            action: 'hide_collection',
            collection_id: collectionId
        }));
    }

    deleteCollection(collectionId) {
        this.hideCollection(collectionId);
    }

    restoreCollection(collectionId) {
        this.socket.send(JSON.stringify({
            action: 'restore_collection',
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
        const id = data.collection_id || data.id;
        let lastRow = $('table tr:last').clone();
        lastRow.attr('collectionlinkitemid', id);
        lastRow.find('td[data-collection-id]').attr('data-collection-id', id);
        lastRow.find('td.listOrderCell').text(data.link_order);
        lastRow.find('a.collectionLink').attr('href', `/core/count-list/display/?listId=${id}&recordType=${data.record_type}`);
        lastRow.find('input.collectionNameElement')
            .val(data.collection_name)
            .attr('id', `input${id}`)
            .attr('collectionlinkitemid', id);
        lastRow
            .find('i.hideCountLinkButton')
            .attr('collectionlinkitemid', id)
            .removeAttr('disabled')
            .removeClass('disabled');
        $('#countCollectionLinkTable').append(lastRow);
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
