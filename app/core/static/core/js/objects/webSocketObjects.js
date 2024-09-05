// import { getCollectionLinkInfo } from '../requestFunctions/requestFunctions.js'

export class CountListWebSocket {
    constructor(listId) {
        this.socket = new WebSocket(`ws://${window.location.host}/ws/count_list/${listId}/`);
        this.initEventListeners();
    }

    initEventListeners() {
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'count_updated') {
                this.updateCountUI(data.record_id, data);
            } else if (data.type === 'on_hand_refreshed') {
                this.updateOnHandUI(data.record_id, data.new_on_hand);
            }
        };

        this.socket.onclose = () => {
            console.error('Count list socket closed unexpectedly');
            this.reconnect();
        };
    }

    reconnect() {
        setTimeout(() => {
            this.socket = new WebSocket(this.socket.url);
            this.initEventListeners();
        }, 1000);
    }

    updateCount(recordId, recordType, recordInformation) {
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
            record_type: recordType
        }));
        // console.log(recordInformation['counted_quantity']);
    }

    refreshOnHand(recordId, recordType) {
        this.socket.send(JSON.stringify({
            action: 'refresh_on_hand',
            record_id: recordId,
            record_type: recordType
        }));
    }

    deleteCount(recordId, recordType) {
        this.socket.send(JSON.stringify({
            action: 'delete_count',
            record_id: recordId,
            record_type: recordType
        }));
    }

    updateCountUI(recordId, data) {
        console.log(data);
        $(`input[data-countrecord-id="${recordId}"].counted_quantity`).val(data['data']['counted_quantity']);
        $(`span[data-countrecord-id="${recordId}"].expected-quantity-span`).text(data['data']['expected_quantity']);
        $(`td[data-countrecord-id="${recordId}"].tbl-cell-variance`).text(data['data']['variance']);
        $(`td[data-countrecord-id="${recordId}"].tbl-cell-counted_date`).text(data['data']['counted_date']);
        $(`textarea[data-countrecord-id="${recordId}"].comment`).val(data['data']['comment']);
        $(`select[data-countrecord-id="${recordId}"].location-selector`).val(data['data']['location']);
        const checkbox = $(`input[data-countrecord-id="${recordId}"].counted-input`);
        checkbox.prop("checked", data['data']['counted']);
        console.log(checkbox);
        console.log(checkbox.parent());
        console.log(data['data']['counted']);
        if (data['data']['counted']) {
            console.log(`data['data']['counted'] is true`);
            checkbox.parent().removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
        } else {
            checkbox.parent().removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
        }
        
    }

    updateOnHandUI(recordId, newOnHand) {
        $(`p[data-countrecord-id="${recordId}"]`).text(newOnHand);
    }

    deleteCountFromUI(recordId) {
        $(`tr[data-countrecord-id="${recordId}"]`).remove()
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
            }
        };

        this.socket.onclose = () => {
            console.error('Count collection socket closed unexpectedly');
            this.reconnect();
        };

        this.socket.onopen = () => {
            console.log("Count collection update WebSocket connection established.");
            this.reconnectAttempts = 0;
        };

        this.socket.onerror = (error) => {
            console.error('Count collection update WebSocket error:', error);
        };

    }

    reconnect() {
        setTimeout(() => {
            this.socket = new WebSocket(this.socket.url);
            this.initEventListeners();
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

    updateCollectionUI(collectionId, newName) {
        $(`#input${collectionId}`).val(newName);
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
        lastRow.find('a.collectionLink').attr('href', '/core/count-list/display/?listId=' + data.id);
        lastRow.find('input.collectionNameInput').val(data.collection_name);
        lastRow.find('i.deleteCountLinkButton').attr('collectionlinkitemid', data.id);
        $('#countCollectionLinkTable').append(lastRow);
        // lastRow.find('td.collectionId').text(collectionLinkInfo.collection_id);
    }
}