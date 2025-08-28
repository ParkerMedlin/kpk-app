$(document).ready(function(){
    let tankSpecs = _getTankSpecs();
    let tankLevels = _getTankLevels();
    makeTankTable(tankSpecs, tankLevels);
    setInterval(() => {  
        let tankSpecs = _getTankSpecs();
        let tankLevels = _getTankLevels();
        makeTankTable(tankSpecs, tankLevels);
    }, 5000);
});

function _getTankSpecs() {
    let tankSpecs;
    $.ajax({
        url: '/core/get-tank-specs/',
        async: false,
        dataType: 'json',
        success: function(data) {
            tankSpecs = data;
        }
    });
    return tankSpecs;
};

function _getTankLevels() {
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

function _getSingleTankLevel(tankIdentifier) {
    let tankLevel;
    $.ajax({
        url: `/core/api/get-single-tank-level/${tankIdentifier}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            tankLevel = data.gallons;
        }
    });
    return tankLevel;
};

function _sortTable(thisTable) {
    let rows, switching, i, x, y, shouldSwitch;
    switching = true;
    while (switching) {
        switching = false; // Start by saying: no switching is done:
        rows = thisTable.rows;
        /* Loop through all table rows (except the
        first, which contains table headers): */
        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("td")[0];
            y = rows[i + 1].getElementsByTagName("td")[0];
            // Check if the two rows should switch places:
            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                shouldSwitch = true;
                break;
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
        }
    }
}

function _cleanupChannelDevice(channelDevice) {
    channelDevice.removeChild(channelDevice.firstChild); // Gray row labelling
    channelDevice.removeChild(channelDevice.firstChild); // Column headers  
    channelDevice.removeChild(channelDevice.firstChild); // Invisible element
    channelDevice.removeChild(channelDevice.lastChild);  // Non-polled channels row
    channelDevice.removeChild(channelDevice.lastChild);  // Another invisible element
    return channelDevice;
}

function _processChannelRows(channelDevice, tankSpecs) {
    const rows = channelDevice.getElementsByTagName('tr');
    for (const row of rows) {
        const thisRowTankLabel = row.firstChild.innerText.toUpperCase().trim();
        row.setAttribute('data-id', thisRowTankLabel);
        
        // Remove unwanted columns (6 total: 4 from end, then 2 more after moving inches)
        for (let i = 0; i < 6; i++) {
            if (i === 4) {
                $(row).children().eq(2).insertBefore($(row).children().eq(1)); // Move the filled inches cell to the left (2 columns before gallons)
            }
            row.removeChild(row.lastChild);
        }

        try {
            const inchesValue = parseFloat($(row).children().eq(1).text());
            let gallonsValue;
            
            // Special handling for DKP tank - get gallons directly
            if (thisRowTankLabel === '18 DKP') {
                gallonsValue = _getSingleTankLevel('18 DKP');
            } else if (thisRowTankLabel === '20 TEAK') {
                gallonsValue = _getSingleTankLevel('20 TEAK');
            } else if (thisRowTankLabel === '21 MSR') {
                gallonsValue = _getSingleTankLevel('21 MSR');
            } else {
                // Normal conversion for all other tanks
                gallonsValue = inchesValue * tankSpecs[thisRowTankLabel]['gallons_per_inch'];
            }
            
            $(row).children().eq(1).text(String(Math.round(gallonsValue)) + " gal");
        } catch(err) {
            console.error('Error converting inches to gallons:', err.message);
        }
        
        // Create and populate new cells
        const contentsDescCell = document.createElement("td");
        const contentsPnCell = document.createElement("td");
        const maxCapacityCell = document.createElement("td");
        
        try {
            contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['item_description'];
            contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['item_code'];
            maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(row).children().eq(1).text()) + " gal";
        } catch(err) {
            console.error(err.message);
        }
        
        // Insert new cells in proper positions
        $(contentsDescCell).insertAfter($(row).children().eq(0));
        $(contentsPnCell).insertAfter($(row).children().eq(0));
        $(maxCapacityCell).insertAfter($(row).children().eq(3));
    }
}

function makeTankTable(tankSpecs, tankLevels){
    let hartHTML = tankLevels.html_string;
    let parser = new DOMParser();
    let doc = parser.parseFromString(hartHTML, 'text/html');
    // Insert the doc HTML string into a div at the top of the page
    
    let rawDataDiv = document.createElement('div');

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
    
    const channelDevices = [1, 2, 3].map(i => {
        const channelDevice = doc.body.querySelector(`#ch${i} p table tbody`);
        _cleanupChannelDevice(channelDevice);
        _processChannelRows(channelDevice, tankSpecs);
        return channelDevice;
    });    

    let tankTableBody = document.getElementById("tankLevelTable");
    let tbodyRemoval = document.getElementsByTagName('tbody');
    while(tbodyRemoval.length){
        tbodyRemoval[0].parentNode.removeChild(tbodyRemoval[0]);
    };
    
    channelDevices.forEach(device => tankTableBody.appendChild(device));
    $('td').find('br').remove();

    let labelCells = document.getElementsByClassName("labelCell");
    for (const cell of labelCells) {
        cell.innerHTML = cell.innerHTML.slice(3);
        cell.innerHTML = "Tank " + cell.innerHTML.trimEnd();
        // Turn this cell into a link to tank usage monitor
        const rowTankId = cell.parentElement?.getAttribute('data-id');
        if (rowTankId) {
            const linkElem = document.createElement('a');
            linkElem.href = `/core/tank-usage/${encodeURIComponent(rowTankId)}/`;
            linkElem.innerText = cell.innerText;
            cell.innerHTML = '';
            cell.appendChild(linkElem);
        }
    }

    _sortTable(tankTableBody);

}; 