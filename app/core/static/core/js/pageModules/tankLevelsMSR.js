$(document).ready(function(){
    let tankSpecs = getTankSpecs();
    let tankLevels = getTankLevels();
    makeTankTable(tankSpecs, tankLevels);
    $('#tankLevelTable tr').each(function() {
        if (!$(this).parent().is('thead') && $(this).data('id') !== '21 MSR') {
            $(this).remove();
        }
    });
    setInterval(() => {  
        let tankSpecs = getTankSpecs();
        let tankLevels = getTankLevels();
        makeTankTable(tankSpecs, tankLevels);
        $('#tankLevelTable tr').each(function() {
            if (!$(this).parent().is('thead') && $(this).data('id') !== '21 MSR') {
                $(this).remove();
            }
        });
    }, 500);
});

function getTankSpecs() {
    let tankSpecs;
    $.ajax({
        url: '/core/get-tank-specs/',
        async: false,
        dataType: 'json',
        success: function(data) {
            tankSpecs = data;
        }
    });
    console.log(tankSpecs);
    return tankSpecs;
};

function getTankLevels() {
    let tankLevels;
    $.ajax({
        url: '/core/get-tank-levels/',
        async: false,
        dataType: 'json',
        success: function(data) {
            tankLevels = data;
        }
    });
    return tankLevels;
};

function sortTable(thisTable) {
    let rows, switching, i, x, y, shouldSwitch;
    switching = true;
    /* Make a loop that will continue until
    no switching has been done: */
    while (switching) {
        // Start by saying: no switching is done:
        switching = false;
        rows = thisTable.rows;
        /* Loop through all table rows (except the
        first, which contains table headers): */
        for (i = 1; i < (rows.length - 1); i++) {
            // Start by saying there should be no switching:
            shouldSwitch = false;
            /* Get the two elements you want to compare,
            one from current row and one from the next: */
            x = rows[i].getElementsByTagName("td")[0];
            y = rows[i + 1].getElementsByTagName("td")[0];
            // Check if the two rows should switch place:
            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                // If so, mark as a switch and break the loop:
                shouldSwitch = true;
                break;
            }
        }
        if (shouldSwitch) {
            /* If a switch has been marked, make the switch
            and mark that a switch has been done: */
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
        }
    }
}
    
// const interval = setInterval( function() {
//     $.getJSON('/core/get-tank-levels/', // send json request
//         function(data) {
//             let hartHTML = data.html_string;
//             document.getElementById("hartPage").innerText=hartHTML;
            
//         }).then(makeTankTable());
// }, 7000);

function makeTankTable(tankSpecs, tankLevels){
    let hartHTML = tankLevels.html_string;
    let parser = new DOMParser();
    let doc = parser.parseFromString(hartHTML, 'text/html');
    let allTableCells = doc.body.getElementsByTagName('td');
    
    for (let tableCell of allTableCells) {
        if (tableCell.innerHTML.includes('????')) {
            tableCell.parentElement.remove();
        };
        if (tableCell.innerHTML.includes('Tag:')) {
            tableCell.innerHTML = tableCell.innerHTML.split(":").pop();
            tableCell.className = "labelCell";
        };
        if (tableCell.innerHTML.includes('PCT')) {
            tableCell.innerHTML = tableCell.innerHTML.split("P")[0] + " %";
        };
        if (tableCell.innerHTML.includes('IN ')) {
            tableCell.innerHTML = tableCell.innerHTML.split("I")[0] + " in";
        };
        if (tableCell.innerHTML.includes('GL ')) {
            tableCell.innerHTML = tableCell.innerHTML.split("G")[0];
        };
        if (tableCell.innerHTML.includes('UKNWN')) {
            tableCell.remove();
        };
        
    };
    

    let channel1Devices = doc.body.querySelector("#ch1 p table tbody");
    channel1Devices.removeChild(channel1Devices.firstChild); // The gray row labelling the table.
    channel1Devices.removeChild(channel1Devices.firstChild); // The row of column headers.
    channel1Devices.removeChild(channel1Devices.firstChild); // An invisible element. If I don't remove this invisible element, everything breaks.
    channel1Devices.removeChild(channel1Devices.lastChild);  // The row which displays which channels are not polled on this device.
    channel1Devices.removeChild(channel1Devices.lastChild);  // Another invisible element. Who knows.
    let channel2Devices = doc.body.querySelector("#ch2 p table tbody");
    channel2Devices.removeChild(channel2Devices.firstChild); // The gray row labelling the table.
    channel2Devices.removeChild(channel2Devices.firstChild); // The row of column headers.
    channel2Devices.removeChild(channel2Devices.firstChild); // An invisible element. If I don't remove this invisible element, everything breaks.
    channel2Devices.removeChild(channel2Devices.lastChild);  // The row which displays which channels are not polled on this device.
    channel2Devices.removeChild(channel2Devices.lastChild);  // Another invisible element. Who knows.
    let channel3Devices = doc.body.querySelector("#ch3 p table tbody");
    channel3Devices.removeChild(channel3Devices.firstChild); // The gray row labelling the table.
    channel3Devices.removeChild(channel3Devices.firstChild); // The row of column headers.
    channel3Devices.removeChild(channel3Devices.firstChild); // An invisible element. If I don't remove this invisible element, everything breaks.
    channel3Devices.removeChild(channel3Devices.lastChild);  // The row which displays which channels are not polled on this device.
    channel3Devices.removeChild(channel3Devices.lastChild);  // Another invisible element. Who knows.

    let thisRowTankLabel;
    const channel1Rows = channel1Devices.getElementsByTagName('tr');
    for (const ch1Row of channel1Rows) {
        thisRowTankLabel = ch1Row.firstChild.innerText.toUpperCase().trim();
        ch1Row.setAttribute('data-id', thisRowTankLabel);
        ch1Row.removeChild(ch1Row.lastChild); // Remove 8thDV Column
        ch1Row.removeChild(ch1Row.lastChild); // Remove 7thDV Column
        ch1Row.removeChild(ch1Row.lastChild); // Remove 6thDV Column
        ch1Row.removeChild(ch1Row.lastChild); // Remove 5thDV Column
        $(ch1Row).children().eq(4).insertBefore($(ch1Row).children().eq(1)); // Move the gallons cell to the left
        ch1Row.removeChild(ch1Row.lastChild); // Remove 3rdDV Column (distance)
        ch1Row.removeChild(ch1Row.lastChild); // Remove 4thDV Column (fill height)
        let contentsDescCell = document.createElement("td");
        let contentsPnCell = document.createElement("td");
        let maxCapacityCell = document.createElement("td");
        try{
            contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['item_description'];
            contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['item_code'];
            maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch1Row).children().eq(1).text()) +" gal";
        } catch(err) {
            console.error(err.message);
        };
        $(contentsDescCell).insertAfter($(ch1Row).children().eq(0));
        $(contentsPnCell).insertAfter($(ch1Row).children().eq(0));
        $(maxCapacityCell).insertAfter($(ch1Row).children().eq(3));
    }
    const channel2Rows = channel2Devices.getElementsByTagName('tr');
    for (const ch2Row of channel2Rows) {
        thisRowTankLabel = ch2Row.firstChild.innerText.toUpperCase().trim();
        ch2Row.setAttribute('data-id', thisRowTankLabel);
        ch2Row.removeChild(ch2Row.lastChild);
        ch2Row.removeChild(ch2Row.lastChild);
        ch2Row.removeChild(ch2Row.lastChild);
        ch2Row.removeChild(ch2Row.lastChild);
        $(ch2Row).children().eq(4).insertBefore($(ch2Row).children().eq(1));
        ch2Row.removeChild(ch2Row.lastChild);
        ch2Row.removeChild(ch2Row.lastChild);
        let contentsDescCell = document.createElement("td");
        let contentsPnCell = document.createElement("td");
        let maxCapacityCell = document.createElement("td");
        try{
            contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['item_description'];
            contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['item_code'];
            maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch2Row).children().eq(1).text()) +" gal";
        } catch(err) {
            console.error(err.message);
        };
        $(contentsDescCell).insertAfter($(ch2Row).children().eq(0));
        $(contentsPnCell).insertAfter($(ch2Row).children().eq(0));
        $(maxCapacityCell).insertAfter($(ch2Row).children().eq(3));
    }
    const channel3Rows = channel3Devices.getElementsByTagName('tr');
    for (const ch3Row of channel3Rows) {
        thisRowTankLabel = ch3Row.firstChild.innerText.toUpperCase().trim();
        ch3Row.setAttribute('data-id', thisRowTankLabel);
        ch3Row.removeChild(ch3Row.lastChild);
        ch3Row.removeChild(ch3Row.lastChild);
        ch3Row.removeChild(ch3Row.lastChild);
        ch3Row.removeChild(ch3Row.lastChild);
        $(ch3Row).children().eq(4).insertBefore($(ch3Row).children().eq(1));
        ch3Row.removeChild(ch3Row.lastChild);
        ch3Row.removeChild(ch3Row.lastChild);
        let contentsDescCell = document.createElement("td");
        let contentsPnCell = document.createElement("td");
        let maxCapacityCell = document.createElement("td");
        try{
            contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['item_description'];
            contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['item_code'];
            maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch3Row).children().eq(1).text()) +" gal";
        } catch(err) {
            console.error(err.message);
        };
        $(contentsDescCell).insertAfter($(ch3Row).children().eq(0));
        $(contentsPnCell).insertAfter($(ch3Row).children().eq(0));
        $(maxCapacityCell).insertAfter($(ch3Row).children().eq(3));
    }
    

    let tankTableBody = document.getElementById("tankLevelTable");
    let tbodyRemoval = document.getElementsByTagName('tbody');
    while(tbodyRemoval.length){
        tbodyRemoval[0].parentNode.removeChild(tbodyRemoval[0]);
    };
    
    tankTableBody.appendChild(channel1Devices);
    tankTableBody.appendChild(channel2Devices);
    tankTableBody.appendChild(channel3Devices);
    $('td').find('br').remove();

    
    
    let labelCells = document.getElementsByClassName("labelCell");
    for (const cell of labelCells) {
        cell.innerHTML = cell.innerHTML.slice(3);
        cell.innerHTML = "Tank " + cell.innerHTML.trimEnd();
    }

    sortTable(tankTableBody);

    // console.log($('tr[data-id="01 1"]').children().eq(3)); // = $('tr[data-id="01 1"]').eq([3]).val()  * 6.53;

}; 