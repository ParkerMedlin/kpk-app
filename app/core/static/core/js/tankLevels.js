let tankSpecs;
        
        window.addEventListener("load", function(e) {
            $.getJSON('/core/gettankspecs/', // send json request
                function(data) {
                    tankSpecs = data;
                    console.log(tankSpecs)
                    return tankSpecs;
                });
            console.log(tankSpecs)
            return tankSpecs;    
        });

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

        const interval = setInterval( function() {
            $.getJSON('/core/gettanklevels/', // send json request
                function(data) {
                    let hartHTML = data.html_string;
                    document.getElementById("hartPage").innerText=hartHTML;
                }).then(makeTankTable());
        }, 5000);

        function makeTankTable(){
            let hartHTML = document.getElementById("hartPage").innerText;
            let parser = new DOMParser();
            let doc = parser.parseFromString(hartHTML, 'text/html');
            let allTableCells = doc.body.getElementsByTagName('td');
            for (let tableCell of allTableCells) {
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
                //if (tableCell.innerHTML.includes('UKNWN')) {
                //    tableCell.remove();
                //};
                if (tableCell.innerHTML.includes('????')) {
                    tableCell.parentElement.remove();
                };
            };
            

            let channel1Devices = doc.body.querySelector("#ch1 p table tbody");
            channel1Devices.removeChild(channel1Devices.firstChild);
            channel1Devices.removeChild(channel1Devices.firstChild);
            channel1Devices.removeChild(channel1Devices.firstChild);
            channel1Devices.removeChild(channel1Devices.lastChild);
            channel1Devices.removeChild(channel1Devices.lastChild);
            let channel2Devices = doc.body.querySelector("#ch2 p table tbody");
            channel2Devices.removeChild(channel2Devices.firstChild);
            channel2Devices.removeChild(channel2Devices.firstChild);
            channel2Devices.removeChild(channel2Devices.firstChild);
            channel2Devices.removeChild(channel2Devices.lastChild);
            channel2Devices.removeChild(channel2Devices.lastChild);
            let channel3Devices = doc.body.querySelector("#ch3 p table tbody");
            channel3Devices.removeChild(channel3Devices.firstChild);
            channel3Devices.removeChild(channel3Devices.firstChild);
            channel3Devices.removeChild(channel3Devices.firstChild);
            channel3Devices.removeChild(channel3Devices.lastChild);
            channel3Devices.removeChild(channel3Devices.lastChild);

            let thisRowTankLabel;
            const channel1Rows = channel1Devices.getElementsByTagName('tr');
            for (const ch1Row of channel1Rows) {
                thisRowTankLabel = ch1Row.firstChild.innerText.toUpperCase().trim();
                ch1Row.setAttribute('data-id', thisRowTankLabel);
                ch1Row.removeChild(ch1Row.lastChild);
                ch1Row.removeChild(ch1Row.lastChild);
                ch1Row.removeChild(ch1Row.lastChild);
                ch1Row.removeChild(ch1Row.lastChild);
                $(ch1Row).children().eq(4).insertBefore($(ch1Row).children().eq(1));
                ch1Row.removeChild(ch1Row.lastChild);
                ch1Row.removeChild(ch1Row.lastChild);
                contentsDescCell = document.createElement("td");
                contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['part_desc'];
                contentsPnCell = document.createElement("td");
                contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['part_number'];
                maxCapacityCell = document.createElement("td");
                maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch1Row).children().eq(1).text()) +" gal";
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
                contentsDescCell = document.createElement("td");
                contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['part_desc'];
                contentsPnCell = document.createElement("td");
                contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['part_number'];
                maxCapacityCell = document.createElement("td");
                maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch2Row).children().eq(1).text()) +" gal";
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
                contentsDescCell = document.createElement("td");
                contentsDescCell.innerText = tankSpecs[thisRowTankLabel]['part_desc'];
                contentsPnCell = document.createElement("td");
                contentsPnCell.innerText = tankSpecs[thisRowTankLabel]['part_number'];
                maxCapacityCell = document.createElement("td");
                maxCapacityCell.innerText = (tankSpecs[thisRowTankLabel]['max_gallons']) - parseInt($(ch3Row).children().eq(1).text()) +" gal";
                $(contentsDescCell).insertAfter($(ch3Row).children().eq(0));
                $(contentsPnCell).insertAfter($(ch3Row).children().eq(0));
                $(maxCapacityCell).insertAfter($(ch3Row).children().eq(3));
            }
            

            let tankTableBody = document.getElementById("tankLevelTable");
            tbodyRemoval = document.getElementsByTagName('tbody');
            while(tbodyRemoval.length){
                tbodyRemoval[0].parentNode.removeChild(tbodyRemoval[0]);
            };
            
            tankTableBody.appendChild(channel1Devices);
            tankTableBody.appendChild(channel2Devices);
            tankTableBody.appendChild(channel3Devices);
            $('td').find('br').remove();

            sortTable(tankTableBody);
            
            let labelCells = document.getElementsByClassName("labelCell");
            for (const cell of labelCells) {
                cell.innerHTML = cell.innerHTML.slice(3);
                cell.innerHTML = "Tank " + cell.innerHTML
            }

        }; 