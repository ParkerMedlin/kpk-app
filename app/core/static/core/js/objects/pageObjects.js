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

export function sendCountRecordChange(eventTarget, thisCountListWebSocket, containerId) {
    function updateDate(eventTarget){
        let correspondingID = eventTarget.attr('correspondingrecordid');
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        $(`td[data-countrecord-id="${correspondingID}"]`).find("input[name*='counted_date']").val(formattedDate);
    };
    const dataCountRecordId = eventTarget.attr('data-countrecord-id');
    updateDate(eventTarget);
    calculateVarianceAndCount(dataCountRecordId);
    // console.log(`getting the container info for `)
    let containers = [];
    const thisContainerTable = $(`table[data-countrecord-id="${dataCountRecordId}"].container-table`);

    // console.log(thisContainerTable.html());
    thisContainerTable.find('tr.containerRow').each(function() {
        // console.log($(this).html());

        let containerData = {
            'container_id': $(this).find(`input.container_id`).val(),
            'container_quantity': $(this).find(`input.container_quantity`).val(),
            'container_type': $(this).find(`select.container_type`).val(),
            'tare_weight': $(this).find(`input.tare_weight`).val(),
        };
        // console.log(containerData);
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
    if (recordType === 'blendcomponent') {
        if (eventTarget.val() === "275gal tote") {
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(125);
        } else if (eventTarget.val() === "poly drum") {
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(22);
        } else if (eventTarget.val() === "regular metal drum") {
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(37);
        } else if (eventTarget.val() === "large poly tote") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(0);
        } else if (eventTarget.val() === "stainless steel tote") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(0);
        } else if (eventTarget.val() === "300gal tote") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(150);
        } else if (eventTarget.val() === "small poly drum") {
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(13);
        } else if (eventTarget.val() === "enzyme metal drum") {
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(50);
        } else if (eventTarget.val() === "plastic pail") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(3);
        } else if (eventTarget.val() === "metal dye_frag pail") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(4);
        } else if (eventTarget.val() === "cardboard box") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(2);
        } else if (eventTarget.val() === "gallon jug") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(1);
        } else if (eventTarget.val() === "storage tank") { 
            const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
            tareWeightInput.val(0);
        }
    } else {
        const tareWeightInput = eventTarget.closest('tr').find('input.tare_weight');
        tareWeightInput.val(0);
    }
}

export class CountListPage {
    constructor(thisCountListWebSocket, thisCountContainerModal) {
        try {
            this.initializeContainerFields();
            this.setUpEventListeners(thisCountListWebSocket, thisCountContainerModal);
            updateCheckBoxCellColors();
            this.setupLabelLinks();
            this.setUpMutationObservers(thisCountListWebSocket);
        } catch(err) {
            console.error(err.message);
        };
    };

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
     * Initializes container fields for each count record in the table
     * 
     * For each count record row:
     * 1. Gets container data from the database for that count record
     * 2. If no containers exist, creates a default empty container row
     * 3. If containers exist, creates a row for each container with its saved data
     * 
     * Each container row includes:
     * - Hidden container ID field
     * - Quantity input
     * - Container type dropdown with options like totes, drums, boxes etc
     * - Tare weight input (hidden for blend records)
     * - Net measurement toggle to indicate whether this is a net or gross measurement(hidden for blend records) 
     * - Delete button
     * 
     * Container rows are appended to the container table body within each count record
     */
    initializeContainerFields() {
        const recordType = getURLParameter('recordType');
        $('#countsTable tbody tr.countRow').each(function() {
            let containerTableBody = $(this).find('tbody.containerTbody');
            let countRecordId = $(this).attr('data-countrecord-id');
            let theseContainers = getContainersFromCount(countRecordId, recordType);
            let tableRows = '';
            if (theseContainers.length === 0) {
                tableRows += `
                    <tr data-container-id="0" data-countrecord-id="${countRecordId}" class="containerRow">
                        <td class='container_id' style="display:none;">
                            <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="0" data-container-id="0">
                        </td>
                        <td class='quantity'><input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="" data-container-id="0"></td>
                        <td class='container_type'>
                            <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="0">
                                <option value="275gal tote" data-countrecord-id="${countRecordId}">275gal Tote</option>
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
                            <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="${recordType === 'blend' ? 125 : 0}" data-container-id="0">
                        </td>
                        <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                            <input type="checkbox" class="net_toggle" data-countrecord-id="${countRecordId}" value=false data-container-id="0">
                        </td>
                        <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="0"></i></td>
                    </tr>
                `;
            } else {
                theseContainers.forEach(container => {
                    tableRows += `
                        <tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
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
                                <input type="checkbox" class="net_toggle" data-countrecord-id="${countRecordId}" value=${container.net_measurement} data-container-id="0">
                            </td>
                            <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i></td>
                        </tr>
                    `;
                });
            };
            containerTableBody.append(tableRows);
        });
    };

    
    /** This function updates the container fields in a count record table:
     * 1. Fetches container data for a specific count record
     * 2. Builds HTML table rows for each container (or a blank row if no containers)
     * 3. Each row contains:
     *    - Hidden container ID
     *    - Quantity input
     *    - Container type dropdown (totes, drums, etc)
     *    - Tare weight input (hidden for blends)
     *    - Net measurement checkbox (hidden for blends)
     *    - Delete button
     * 4. Sets up event handlers for:
     *    - Container type changes (updates tare weight & sends updates)
     *    - Adding new container rows
     *    - Deleting container rows  
     *    - Quantity changes
     * 5. Focuses cursor on the quantity input of the updated container
     */

    updateContainerFields(countRecordId, recordType, containerId, thisCountListWebSocket) {
        // Add event handler for net measurement toggle to control tare weight field

        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        // THIS IS THE LAST THING I CHANGED
        
        $(document).on('change', '.net_toggle', function() {
            const countRecordId = $(this).data('countrecord-id');
            const containerId = $(this).data('container-id');
            const tareWeightInput = $(this).closest('tr').find('.tare_weight input');
            
            if ($(this).is(':checked')) {
                tareWeightInput.prop('disabled', true);
                tareWeightInput.val('');
            } else {
                tareWeightInput.prop('disabled', false);
            }
            
            // Trigger update
            const eventTarget = $(`[data-countrecord-id="${countRecordId}"]`).first();
            sendCountRecordChange(eventTarget, thisCountListWebSocket, containerId);
        });

        let theseContainers = getContainersFromCount(countRecordId, recordType);
        console.log(`populating the containers with data retreived from the database: ${theseContainers}`);
        let tableRows = '';
        let containerTableBody = $(`#countsTable tbody tr[data-countrecord-id=${countRecordId}]`).find('table.container-table')
        // console.log(containerId)
        // theseContainers.forEach(container => {
        //     console.log(container);

        // });

        // console.log(containerTableBody.html());
        if (theseContainers.length === 0) {
            tableRows += `<tr data-container-id="0" data-countrecord-id="${countRecordId}" class="containerRow">
                    <td class='container_id' style="display:none;">
                        <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="0" data-container-id="0">
                    </td>
                    <td class='quantity'><input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="" data-container-id="0"></td>
                    <td class='container_type'>
                        <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="0">
                            <option value="275gal tote" data-countrecord-id="${countRecordId}">275gal Tote</option>
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
                        <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="" data-container-id="0">
                    </td>
                    <td class="netMeasurement ${recordType === 'blend' ? 'hidden' : ''} net_measurement">
                        <input type="checkbox" class="net_toggle" data-countrecord-id="${countRecordId}" value=false data-container-id="0">
                    </td>
                    <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="0"></i></td>
                </tr>
            `;
        } else {
            theseContainers.forEach(container => {
                tableRows += `<tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
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
                            <input type="checkbox" class="net_toggle" data-countrecord-id="${countRecordId}" value=${container.net_measurement} data-container-id="0">
                        </td>
                        <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i></td>
                    </tr>
                `;
            });
        }

        containerTableBody.find('tbody').children().remove();
        containerTableBody.find('tbody').append(tableRows);
        
        $(containerTableBody).find('select.container_type').off('change');
        $(containerTableBody).find('select.container_type').on('change', function() {
            const containerId = $(this).attr('data-container-id');
            console.log(`Passing containerId: ${containerId}`);
            updateTareWeight($(this), containerId);
            sendCountRecordChange($(this), thisCountListWebSocket, containerId);
        });

        $(containerTableBody).find('.add-container-row').off('click');
        $(containerTableBody).find('.add-container-row').click(function() {
            const recordId = this.getAttribute('data-countrecord-id');
            const table = $(`table[data-countrecord-id="${recordId}"]`);
            const rows = document.querySelectorAll(`table[data-countrecord-id="${recordId}"] tr`);
            const lastRow = rows[rows.length - 1];
            const newRow = lastRow.cloneNode(true);
            $(newRow).find('input').val('');
            const newRowContainerId = parseInt($(lastRow).attr('data-container-id')) + 1;
            $(newRow).attr('data-container-id', newRowContainerId);
            $(newRow).find('input.container_id').val(newRowContainerId);
            $(newRow).find('input.container_quantity').attr('data-container-id', newRowContainerId);
            $(newRow).find('.row-clear').click(function() {
                $(this).closest('tr').remove();
            });
            $(newRow).find('input.container_quantity').on('keyup', function() {
                calculateVarianceAndCount(recordId);
                sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            });
            $(newRow).find('select.container_type').on('change', function() {
                const containerId = $(this).attr('data-container-id');
                updateTareWeight($(this), containerId);
                sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            });
            $(newRow).find('input.container_id').on('keyup', function() {
                calculateVarianceAndCount(recordId);
                sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            });
            table.find('tbody tr:last').after(newRow);
            sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
        });

        $(containerTableBody).find('.row-clear').off('click');
        $(containerTableBody).find('.row-clear').click(function() {
            $(this).closest('tr').remove();
            const containerId = $(this).attr('data-container-id');
            sendCountRecordChange($(this), thisCountListWebSocket, containerId);
        });

        // $(containerTableBody).find('.container_quantity').off('keyup');
        $(containerTableBody).find('.container_quantity').on('change', function() {
            const containerId = $(this).attr('data-container-id');
            sendCountRecordChange($(this), thisCountListWebSocket, containerId);
        });

        const thisContainer = theseContainers[containerId];
        const thisContainerRow = $(`tr[data-countrecord-id="${countRecordId}"][data-container-id="${containerId}"]`);
        const quantityInput = thisContainerRow.find('input.container_quantity');
        quantityInput.on('focus', function() {
            let value = $(this).val();
            // Use setTimeout to handle Chrome bug where cursor doesn't move to the end immediately
            setTimeout(() => {
                // For 'number' input types, replace the value to move the cursor to the end
                if ($(this).attr('type') === 'number') {
                    $(this).val(null).val(value); // Temporarily set to null and back to value to move cursor
                } else if ($(this).attr('type') === 'text') {
                    let valueLength = value.length;
                    this.setSelectionRange(valueLength, valueLength); // For text inputs, use setSelectionRange
                }
            }, 0); // Delay of 0ms to ensure it runs after the focus event
        });
        quantityInput.focus();
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

        // ALL THE MODAL STUFF:
        $('select.container_type').off('change');
        $('select.container_type').on('change', function() {
            const containerId = $(this).closest('tr').attr('data-container-id');
            updateTareWeight($(this), containerId);
            console.log(`Passing containerId: ${containerId}`);
            sendCountRecordChange($(this), thisCountListWebSocket, containerId);
        });

        $('.add-container-row').off('click');
        $('.add-container-row').click(function() {
            const recordId = this.getAttribute('data-countrecord-id');
            const table = $(`table[data-countrecord-id="${recordId}"]`);
            const rows = document.querySelectorAll(`table[data-countrecord-id="${recordId}"] tr`);
            const lastRow = rows[rows.length - 1];
            const newRow = lastRow.cloneNode(true);
            $(newRow).find('input').val('');
            const newRowContainerId = parseInt($(lastRow).attr('data-container-id')) + 1;
            $(newRow).attr('data-container-id', newRowContainerId);
            $(newRow).find('input.container_id').val(newRowContainerId);
            $(newRow).find('input.container_quantity').attr('data-container-id', newRowContainerId);
            $(newRow).find('.row-clear').click(function() {
                $(this).closest('tr').remove();
            });
            $(newRow).find('input.container_quantity').on('change', function() {
                calculateVarianceAndCount(recordId);
                sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            });
            $(newRow).find('select.container_type').on('change', function() {
                sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            });
            // $(newRow).find('input.container_id').on('keyup', function() {
            //     calculateVarianceAndCount(recordId);
            //     sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
            // });
            table.find('tbody tr:last').after(newRow);
            sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
        });

        $('.row-clear').off('click');
        $('.row-clear').click(function() {
            $(this).closest('tr').remove();
            const containerId = $(this).attr('data-container-id');
            
            sendCountRecordChange($(this), thisCountListWebSocket, containerId);
        });

        $('.container_quantity').off('keyup');
        $('.container_quantity').on('change', function(e) {
            if (e.key !== '.') {
                const containerId = $(this).attr('data-container-id');
                // const countRecord = $(this).attr('data-countrecord-id');
                // console.log(`sending an update for countrecord ${countRecord}, container ${containerId}`);
                sendCountRecordChange($(this), thisCountListWebSocket, containerId);
            }
        });
    };

    setUpMutationObservers(thisCountListWebSocket) {
        // let setUpEventListeners = this.setUpEventListeners;
        let updateContainerFields = this.updateContainerFields;

        const containerMonitorObserver = new MutationObserver((mutationsList) => {
            for (let mutation of mutationsList) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-container-id-updated') {
                    const countRecordId = mutation.target.getAttribute('data-countrecord-id');
                    const updatedContainerId = mutation.target.getAttribute('data-container-id-updated');
                    const recordType = getURLParameter('recordType');
                    console.log(`Container monitor updated for countRecordId: ${countRecordId}, new containerId: ${updatedContainerId}`);
                    updateContainerFields(countRecordId, recordType, updatedContainerId, thisCountListWebSocket);
                    // setUpEventListeners(thisCountListWebSocket);
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
                let orderNumber = $(this).find('td:eq(0)').text();
                let lotNumber = $(this).find('td:eq(4)').attr('lot-number');
                // Skip rows with an empty value in the second cell.
                if (lotNumber.trim() !== '') {
                    deskScheduleDict[lotNumber] = orderNumber;
                }
            });
            if (thisRow.hasClass('Desk_1')) {
                deskScheduleDict["desk"] = "Desk_1";
            } else if (thisRow.hasClass('Desk_2')) {
                deskScheduleDict["desk"] = "Desk_2";
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