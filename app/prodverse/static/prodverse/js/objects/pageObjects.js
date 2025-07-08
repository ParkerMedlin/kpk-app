import { CreateBlendLabelButton } from '../objects/buttonObjects.js'
import { getBlendQuantitiesPerBill, getMatchingLotNumbers, getToteClassificationData, getAllFoamFactors } from '../requestFunctions/requestFunctions.js'


export class ProductionSchedulePage {
    constructor() {
        try {
            // websocket
            this.scheduleUpdateSocket = null;
            this.cartonPrintSocket = null;
            this.currentProdLine = null;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
            this.reconnectDelay = 5000;
            this.initTruncatableCells = this.initTruncatableCells.bind(this);
            this.getJulianDate = this.getJulianDate.bind(this);
            this.addItemCodeLinks = this.addItemCodeLinks.bind(this);
            this.getTextNodes = this.getTextNodes.bind(this);
            this.unhideTruncatedText = this.unhideTruncatedText.bind(this);
            this.initCartonPrintToggles = this.initCartonPrintToggles.bind(this);
            this.loadSchedule = this.loadSchedule.bind(this);
            this.determineProdLine = this.determineProdLine.bind(this);
            this.appendCacheBusting = this.appendCacheBusting.bind(this);
            this.sanitizeAndCustomize = this.sanitizeAndCustomize.bind(this);
            this.cartonPrintStatuses = {};
            this.setupProductionSchedule();
            this.initScheduleUpdateWebSocket();
        } catch(err) {
            console.error(err.message);
        };
    };

    initWebSockets() {
        this.initScheduleUpdateWebSocket();
    }

    setupProductionSchedule() {
        const includes = $('[data-include]');
        this.includes = includes; // Store includes in the class instance
        this.staticpath = "/dynamic/html/"; // Store staticpath in the class instance

        // Attach event listeners to buttons
        ['horix', 'inline', 'blister', 'pd', 'jb', 'oil', 'pouch', 'kit'].forEach(type => {
            $(`#${type}button`).click(() => {
                const fileName = `${type}schedule.html`;
                this.loadSchedule(fileName);
                localStorage.setItem("lastViewedSchedule", fileName);
                this.currentProdLine = type.toUpperCase();
                this.initCartonPrintToggles(this.currentProdLine);
            });
        });

        // Load the last viewed schedule or default to inline
        const lastViewedSchedule = localStorage.getItem("lastViewedSchedule") || "inlineschedule.html";
        this.loadSchedule(lastViewedSchedule);
    }

    loadSchedule(fileName) {
        if (!fileName) {
            console.error("loadSchedule called with an invalid fileName:", fileName);
            return;
        }

        const prodLine = this.determineProdLine(fileName);
        const filePath = `${this.staticpath}${fileName}`;
        const fileBusted = this.appendCacheBusting(filePath);

        this.includes.load(fileBusted, () => {
            this.sanitizeAndCustomize(prodLine, fileName);
            this.currentSchedule = fileName;
            this.currentProdLine = prodLine;
            this.initCartonPrintWebSocket(prodLine);
        });
    }

    determineProdLine(scheduleFileName) {
        if (!scheduleFileName) {
            console.error("determineProdLine called with an invalid scheduleFileName:", scheduleFileName);
            return;
        }

        let prodLine;
        if (scheduleFileName.includes("horix")) {
            prodLine = 'Hx';
        } else if (scheduleFileName.includes("inline")) {
            prodLine = 'INLINE';
        } else if (scheduleFileName.includes("blister")) {
            prodLine = 'BLISTER';
        } else if (scheduleFileName.includes("pdschedule")) {
            prodLine = 'PDLINE';
        } else if (scheduleFileName.includes("jbschedule")) {
            prodLine = 'JBLINE';
        } else if (scheduleFileName.includes("oil")) {
            prodLine = 'OILLINE';
        } else if (scheduleFileName.includes("kit")) {
            prodLine = 'KITSLINE';
        } else if (scheduleFileName.includes("pouch")) {
            prodLine = 'POUCH';
        } else {
            console.error("Unknown production line for scheduleFileName:", scheduleFileName);
        }
        return prodLine;
    }

    appendCacheBusting(file) {
        const uniqueid = new Date().getTime();
        return file + '?v=' + uniqueid;
    }

    sanitizeAndCustomize(prodLine, fileName) {
        this.getTextNodes().forEach(node => node.nodeValue = node.nodeValue.replace(/[^\x00-\x7F]/g, ""));
        this.unhideTruncatedText();
        const scheduleCustomizations = {
            'blisterschedule.html': this.removeColumns(10, 9, 6),
            'kitschedule.html': this.removeColumns(6)
        };
        scheduleCustomizations[fileName]?.();
        this.addItemCodeLinks(prodLine);
        this.initCartonPrintToggles(prodLine);
        this.initTruncatableCells();
    }

    removeColumns(...indices) {
        return () => indices.forEach(i => $(`td:nth-child(${i})`).remove());
    }

    initScheduleUpdateWebSocket() {
        if (this.scheduleUpdateSocket) {
            this.scheduleUpdateSocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/schedule_updates/`);

        ws.onopen = () => {
            console.log("Schedule update WebSocket connection established.");
            this.reconnectAttempts = 0;
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("WebSocket message received:", data);

            const fileName = data.message?.file_name;
            if (!fileName) {
                console.error("WebSocket message does not contain a valid file_name:", data);
                return;
            }

            if (fileName === this.currentSchedule) {
                this.loadSchedule(fileName);
            }
        };

        ws.onerror = (error) => {
            console.error('Schedule update WebSocket error:', error);
        };

        ws.onclose = (event) => {
            console.log('Schedule update WebSocket connection closed. Attempting to reconnect...');
            if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.initScheduleUpdateWebSocket();
                }, this.reconnectDelay);
            }
        };

        this.scheduleUpdateSocket = ws;
    }

    addItemCodeLinks(prodLine) {
        const tableRows = Array.from(document.querySelectorAll('table tr'));
        const getJulianDate = this.getJulianDate;
        let qtyIndex;
        let itemCodeIndex;
        
        for (const [i, row] of tableRows.entries()) {
            const cells = Array.from(row.querySelectorAll('td'));
            for (const [j, cell] of cells.entries()) {
                if (cell.textContent.trim() === "Qty") {
                    qtyIndex = j + 1;
                    break;
                }
            }
            if (qtyIndex) {
            break;
            }
        }

        for (const [i, row] of tableRows.entries()) {
            const cells = Array.from(row.querySelectorAll('td'));
            for (const [j, cell] of cells.entries()) {
                if (cell.textContent.trim() === "P/N") {
                    itemCodeIndex = j + 1;
                    break;
                }
            }
            if (itemCodeIndex) {
            break;
            }
        }
        
        const cells = Array.from(document.querySelectorAll('td:nth-child(3)'));
        const poNumbers = Array.from(document.querySelectorAll('td:nth-child(4)'));
        let blendCells = Array.from(document.querySelectorAll('td:nth-child(6)'));
        
        
        cells.forEach((cell, index) => {
            const text = cell.textContent.trim();
            if (index == 0) {
                let formattedDate = new Date(text).toLocaleDateString("en-US", { timeZone: "America/Chicago" });
                const today = new Date().toLocaleDateString("en-US", { timeZone: "America/Chicago" });
                if (document.getElementById('Harvey')) {
                    document.getElementById('Harvey').remove();
                }
                if (document.getElementById('offlineText')) {
                    document.getElementById('offlineText').remove();
                }
                console.log(`today's date: ${today}`);
                console.log(`schedule cell C1 date: ${formattedDate}`);
                if (formattedDate < today || text == '' ) {
                    
                    
                    const offlineText = document.createElement('div');
                    offlineText.id = 'offlineText'
                    offlineText.textContent = 'NOTE: schedule is out of date.'; 
                    offlineText.style.position = 'fixed';
                    offlineText.style.top = '50%';
                    offlineText.style.left = '50%';
                    offlineText.style.transform = 'translate(-50%, -50%)';
                    offlineText.style.color = 'black';
                    offlineText.style.fontSize = '8em';
                    offlineText.style.zIndex = '1001';
                    offlineText.style.width = '100%';
                    offlineText.style.textAlign = 'center';
                    offlineText.style.fontFamily = 'Impact, Charcoal, sans-serif';
                    offlineText.style.textShadow = '2px 2px 5px #000000';
                    document.body.appendChild(offlineText);
                    
                    cell.style.backgroundColor = 'red';
                };
            };
            const quantity = parseInt(cell.parentElement.querySelector(`td:nth-child(${qtyIndex})`).textContent.trim().replace(',', ''), 10);

            let runDate;
            let gallonMultiplier;
            if (prodLine == 'Hx' || prodLine == 'Totes' || prodLine == 'Pails' || prodLine == 'Dm') {
                runDate = cell.parentElement.querySelector(`td:nth-child(11)`).textContent.replaceAll("/","-");
                if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('drum')) {
                    prodLine = "Dm";
                    gallonMultiplier = 55;
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('265 gal tote')) {
                    prodLine = "Totes";
                    gallonMultiplier = 265;
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('275 gal tote')) {
                    prodLine = "Totes";
                    gallonMultiplier = 275;
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('pail')) {
                    prodLine = "Pails";
                    gallonMultiplier = 5;
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('6-1gal')) {
                    prodLine = "Hx";
                    gallonMultiplier = 6;
                }
            }
            if (text.length > 0 && !text.includes(' ') && text !== "P/N" && !/^\d{2}\/\d{2}\/\d{4}$/.test(text) && !/^\d{1}\/\d{2}\/\d{4}$/.test(text) && !/^\d{1}\/\d{1}\/\d{4}$/.test(text)  && !/^\d{2}\/\d{1}\/\d{4}$/.test(text)) {
                const itemCode = text;
                const secondColumnText = cell.closest('tr').querySelector('td:nth-child(2)').textContent.trim();
                const includeToggle = !secondColumnText.includes('P');    
                const qty = parseInt(cell.parentElement.querySelector(`td:nth-child(${qtyIndex})`).textContent.trim().replace(',', ''), 10);          
                const poNumber = poNumbers[index].textContent.trim();
                const julianDate = getJulianDate();
                const totalGal = gallonMultiplier * quantity;
                const dropdownHTML = `
                    <div class="dropdown">
                    <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown">${itemCode}</a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/prodverse/spec-sheet/${encodeURIComponent(itemCode)}/${encodeURIComponent(poNumber)}/${encodeURIComponent(julianDate)}" target="blank">
                        Spec Sheet
                        </a></li>
                        <li><a class="dropdown-item" href="/prodverse/pick-ticket/${encodeURIComponent(itemCode)}?schedule-quantity=${encodeURIComponent(qty)}" target="blank">
                        Pick Ticket
                        </a></li>
                        <li><a class="dropdown-item issueSheetLink" href="/core/display-this-issue-sheet/${encodeURIComponent(prodLine)}/${encodeURIComponent(itemCode)}?runDate=${runDate}&totalGal=${totalGal}" target="blank">
                        Issue Sheet
                        </a></li>
                        ${includeToggle ? `
                        <li><a class="dropdown-item toggleCartonPrint" href="#" data-item-code="${itemCode}">
                        Toggle Carton Printed
                        </a></li>
                        ` : ''}
                    </ul>
                    </div>
                `;
                
                cell.innerHTML = dropdownHTML;
                cell.style.cursor = "pointer";
            }            
        });

        const foamFactorData = getAllFoamFactors();
        const blendQuantitiesPerBill = getBlendQuantitiesPerBill();
        const toteClassificationData = getToteClassificationData();
        if (prodLine == 'Hx' || prodLine == 'Dm') {
            blendCells = Array.from(document.querySelectorAll('td:nth-child(7)'));
        };
        blendCells.forEach((cell, index) => {
            let runDate;
            if (prodLine == 'Hx' || prodLine == 'Totes' || prodLine == 'Pails' || prodLine == 'Dm') {
                runDate = cell.parentElement.querySelector(`td:nth-child(11)`).textContent.replaceAll("/","-");
            };
            if (prodLine == 'Hx' || prodLine == 'Totes' || prodLine == 'Pails' || prodLine == 'Dm') {
                runDate = cell.parentElement.querySelector(`td:nth-child(11)`).textContent.replaceAll("/","-");
                if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('drum')) {
                    prodLine = "Dm";
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('265 gal tote')) {
                    prodLine = "Totes";
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('275 gal tote')) {
                    prodLine = "Totes";
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('pail')) {
                    prodLine = "Pails";
                } else if (cell.parentElement.querySelector(`td:nth-child(9)`).textContent.includes('6-1gal')) {
                    prodLine = "Hx";
                }
            }
            const quantity = parseInt(cell.parentElement.querySelector(`td:nth-child(${qtyIndex})`).textContent.trim().replace(',', ''), 10);
            // const itemCode = cell.parentElement.querySelector(`td:nth-child(${itemCodeIndex})`).textContent.trim();
            const itemCode = cell.parentElement.querySelector(`td:nth-child(${itemCodeIndex})`).textContent.trim().split(" ")[0].trim();
            const blendItemCode = cell.textContent.trim();
            const encodedItemCode = btoa(blendItemCode)
            const qtyPerBill = blendQuantitiesPerBill[itemCode]
            const toteClassificationRow = toteClassificationData[blendItemCode]
            const toteClassification = toteClassificationRow ? toteClassificationRow.tote_classification : 'Unknown';
            const hoseClassification = toteClassificationRow ? toteClassificationRow.hose_color : 'Unknown';
            const foamFactor = foamFactorData[itemCode] || 1;
            const blendQuantity = quantity * qtyPerBill * 1.1 * foamFactor;
            const dropdownHTML = `
                    <div class="dropdown">
                        <a class="dropdown-toggle blendLabelDropdownLink" type="button" data-bs-toggle="dropdown">${blendItemCode}</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" style="pointer-events: none;">${blendQuantity} gal</a></li>
                            <li><a class="dropdown-item blendLabelLink" data-encoded-item-code=${encodedItemCode}>
                            Blend Label
                            </a></li>
                            <li><a class="dropdown-item issueSheetLink" href="/core/display-this-issue-sheet/${encodeURIComponent(prodLine)}/${encodeURIComponent(itemCode)}?runDate=${runDate}&totalGal=${blendQuantity}" target="blank">
                            Issue Sheet
                            </a></li>
                            <li>
                            <a class="dropdown-item" style="pointer-events: none;">Hose Classification: ${hoseClassification}</a>
                            </li>
                            <li>
                            <a class="dropdown-item ${hoseClassification}" style="pointer-events: none;">.</a>
                            </li>
                            <li>
                            <a class="dropdown-item" style="pointer-events: none;">Tote Classification: ${toteClassification}</a>
                            </li>
                        </ul>
                    </div>
                `;
            cell.innerHTML = dropdownHTML;
            cell.style.cursor = "pointer";
        });
        const blendLabelLinks = document.querySelectorAll(".blendLabelLink");
        let dialog = document.querySelector('#blendLabelDialog');
        blendLabelLinks.forEach(function(link) {
            let thisCreateBlendLabelButton = new CreateBlendLabelButton(link);
            link.addEventListener('click', function(event) {
                dialog.showModal();
                $("#blendLabelPrintButton").attr("data-encoded-item-code", event.currentTarget.getAttribute("data-encoded-item-code"));
                // $("#blendLabelPrintButton").attr("data-lot-number", event.currentTarget.getAttribute("data-lot-number"));
            });
        });

        // document.querySelectorAll(".blendLotNumbersLink").forEach(function(link) {
        //     link.addEventListener('click', function(event) {
        //         event.preventDefault();
        //         const encodedItemCode = link.attr("");
        //         const runDate = ;
        //         getMatchingLotNumbers(encodedItemCode, prodLine, runDate)
        //             .then(result => {
        //                 console.log(result);
        //             })
        //             .catch(error => {
        //                 console.error('Error fetching matching lot numbers:', error);
        //             });
        //         // $("#lotNumbersDisplayModal").show();
        //     });
        // });
    };

    getJulianDate() {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 0);
        const diff = now - start;
        const oneDay = 1000 * 60 * 60 * 24;
        const julianDate = Math.floor(diff / oneDay);
        const yearDigits = now.getFullYear().toString().slice(-2);
        return yearDigits + julianDate;
    };

    getTextNodes() {
        const textNodes = [];
        // Get all the elements in the page and cache the selection
        const elements = $('*');
        // Iterate over the elements using a for...of loop
        for (const element of elements) {
            // Get the text nodes from the element's contents
            const nodes = $(element).contents().filter(function() {
            return this.nodeType === 3; // Text node
            });
            // Add the text nodes to the textNodes array
            textNodes.push(...nodes);
        }
        return textNodes;
    };

    unhideTruncatedText() {
        const spans = document.querySelectorAll('table span');
        console.log('unhideTruncatedText called, found ' + spans.length + ' elements');
        spans.forEach(span => {
            span.style.display = '';
        });
    };

    initTruncatableCells() {
        const rows = document.querySelectorAll('tr');
        rows.forEach((row, index) => {
            if (index > 3) { // Apply only to rows after the fourth row
                const fifthTd = row.querySelector('td:nth-child(5)');
                if (fifthTd) {
                    fifthTd.classList.add('truncatable-cell');
                    
                    // Check if content is truncated
                    const isTextTruncated = fifthTd.scrollWidth > fifthTd.clientWidth;
                    if (isTextTruncated) {
                        fifthTd.classList.add('truncated');
                        fifthTd.addEventListener('click', function(e) {
                            e.stopPropagation();
                            this.classList.toggle('expanded');
                        });
                    }
                }
            }
        });

        // Close expanded cells when clicking outside
        document.addEventListener('click', function() {
            document.querySelectorAll('.truncatable-cell.expanded').forEach(td => td.classList.remove('expanded'));
        });
    };

    initCartonPrintWebSocket(prodLine) {
        if (this.cartonPrintSocket) {
            this.cartonPrintSocket.close();
        }
    
        const today = new Date().toISOString().split('T')[0];
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/carton-print/${today}/${prodLine}/`);
    
        ws.onopen = () => {
            console.log(`Carton print WebSocket connection established for ${prodLine}.`);
            this.reconnectAttempts = 0;
        };
    
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const $toggle = $(`.toggleCartonPrint[data-item-code="${data.itemCode}"]`);
            this.updateUI($toggle, data.isPrinted);
            $toggle.prop('disabled', false);
        };
    
        ws.onerror = (error) => {
            console.error(`Carton print WebSocket error for ${prodLine}:`, error);
        };
    
        ws.onclose = (event) => {
            console.log(`Carton print WebSocket connection closed for ${prodLine}. Attempting to reconnect...`);
            if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.initCartonPrintWebSocket(prodLine);
                }, this.reconnectDelay);
            }
        };
    
        this.cartonPrintSocket = ws;
    }

    initCartonPrintToggles(prodLine) {
        const today = new Date().toISOString().split('T')[0];
    
        // Set data-item-code attribute for each toggle button
        $('.toggleCartonPrint').each(function() {
            const $toggle = $(this);
            const $row = $toggle.closest('tr');
            const partNumber = $row.find('td:nth-child(3)').text().trim().split(/\s+/)[0];
            const poNumber = $row.find('td:nth-child(4)').text().trim();
            const qty = prodLine == 'Hx' ? $row.find('td:nth-child(11)').text().trim() : $row.find('td:nth-child(8)').text().trim();
            const itemCode = `${partNumber}_${poNumber}_${qty}`; // Unique identifier

            $toggle.attr('data-item-code', itemCode);
        });
    
        // Fetch initial print status from the server
        this.fetchInitialPrintStatus(today, prodLine);
    
        // Remove any existing click handlers before adding a new one
        $(document).off('click', '.toggleCartonPrint');
    
        // Click handler
        $(document).on('click', '.toggleCartonPrint', (e) => {
            e.preventDefault();
            const $toggle = $(e.currentTarget);
            const itemCode = $toggle.data('item-code');
            const isPrinted = !$toggle.closest('tr').find('td:nth-child(3)').hasClass('carton-printed');

            // Disable the toggle button to prevent double-clicking
            $toggle.prop('disabled', true);

            // Send update to server
            if (this.cartonPrintSocket && this.cartonPrintSocket.readyState === WebSocket.OPEN) {
                const payload = {
                    'date': today,
                    'prodLine': prodLine,
                    'itemCode': itemCode,
                    'isPrinted': isPrinted
                };
                console.log("Sending to server:", payload);
                this.cartonPrintSocket.send(JSON.stringify(payload));
            } else {
                console.error("Carton print WebSocket is not open. ReadyState: " + (this.cartonPrintSocket ? this.cartonPrintSocket.readyState : 'undefined'));
                // Re-enable the toggle button if the WebSocket is not open
                $toggle.prop('disabled', false);
            }
        });
    }
    
    fetchInitialPrintStatus(date, prodLine) {
        $.ajax({
            url: `/prodverse/production-schedule/get-carton-print-status/`,
            method: 'GET',
            data: { date: date, prodLine: prodLine },
            success: (response) => {
                response.statuses.forEach(status => {
                    const $toggle = $(`.toggleCartonPrint[data-item-code="${status.itemCode}"]`);
                    this.updateUI($toggle, status.isPrinted);
                });
            },
            error: function(error) {
                console.error("Error fetching carton print status:", error);
            }
        });
    }
    
    updateUI($toggle, isPrinted) {
        $toggle.text(isPrinted ? 'Unmark Carton Printed' : 'Mark Carton Printed');
        const $row = $toggle.closest('tr');
        const $cells = $row.find('td:nth-child(3), td:nth-child(4), td:nth-child(5)');
        $cells.toggleClass('carton-printed', isPrinted);
    }

}

export class SpecSheetPage {
    constructor() {
        try {
            // Initialize this.state_json by parsing the content of the #state_json div
            const stateJsonElement = document.getElementById("state_json");
            const stateJsonText = stateJsonElement ? stateJsonElement.textContent : null;
            if (stateJsonText && stateJsonText.trim() !== "") {
                try {
                    this.state_json = JSON.parse(stateJsonText);
                } catch (e) {
                    console.error("Error parsing initial state_json from DOM:", e, "Raw text:", stateJsonText);
                    this.state_json = {}; 
                }
            } else {
                this.state_json = {}; // Default if div is missing, empty, or contains only whitespace
            }

            this.socket = null;
            this.hasLocalChanges = false;
            this.debounceTimer = null;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
            this.reconnectDelay = 3000; // 3 seconds
            
            this.spec_id = this.extractSpecIdFromUrl();
            console.log("Spec ID initialized in constructor:", this.spec_id);
            
            this.lastBroadcastState = null; // Track last broadcasted state to avoid loops
            this.setupSpecSheetPage();
            this.drawSignature = this.drawSignature.bind(this);
            this.savePdf = this.savePdf.bind(this);
            this.initWebSocket = this.initWebSocket.bind(this);
            this.updateServerState = this.updateServerState.bind(this);
            this.initWebSocket();
            this.initializeFromStateJson();
            $("#savePdf").on("click", this.savePdf);
            this.drawSignature($('#signature1').val(), document.getElementById('canvas1'));
            this.drawSignature($('#signature2').val(), document.getElementById('canvas2'));
            this.populatePrintDate();
        } catch(err) {
            console.error(err.message);
        };
    };
    
    extractSpecIdFromUrl() {
        // Extract full spec ID from URL with proper path analysis
        const path = window.location.pathname;
        const specSheetRegex = /\/prodverse\/spec-sheet\/([^\/]+)\/([^\/]+)\/([^\/]+)/;
        const match = path.match(specSheetRegex);
        
        if (match && match.length >= 4) {
            // We have all three components: itemCode, poNumber, and julianDate
            const itemCode = decodeURIComponent(match[1]);
            const poNumber = decodeURIComponent(match[2]);
            const julianDate = decodeURIComponent(match[3]);
            
            // Create a composite unique ID
            return `${itemCode}_${poNumber}_${julianDate}`;
        }
        
        // Fallback to simpler parsing if regex didn't match
        const pathArray = window.location.pathname.split('/');
        const specSheetIndex = pathArray.indexOf('spec-sheet');
        
        if (specSheetIndex !== -1 && pathArray.length > specSheetIndex + 1) {
            // Try to construct from path segments
            const remainingPath = pathArray.slice(specSheetIndex + 1).join('_');
            return remainingPath;
        }
        
        // Absolute fallback to full path as a unique identifier
        return window.location.pathname.replace(/\//g, '_');
    }
    
    initWebSocket() {
        if (this.socket) {
            this.socket.close();
        }
        
        try {
            // Ensure spec_id is set before creating the connection
            if (!this.spec_id) {
                this.spec_id = this.extractSpecIdFromUrl();
            }
            console.log("Creating WebSocket connection with spec_id:", this.spec_id);
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/spec_sheet/${encodeURIComponent(this.spec_id)}/`);
            
            this.socket.onopen = () => {
                console.log(`WebSocket connection established for spec sheet: ${this.spec_id}`);
                this.reconnectAttempts = 0;
            };
            
            this.socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'spec_sheet_update') {
                    this.handleWebSocketUpdate(message.data);
                } else if (message.type === 'initial_state') {
                    console.log("Received initial state from server:", message.data);
                    this.applyInitialState(message.data);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error(`WebSocket error for spec sheet: ${this.spec_id}`, error);
            };
            
            this.socket.onclose = (event) => {
                console.log(`WebSocket connection closed for spec sheet: ${this.spec_id}. ${event.wasClean ? 'Clean close' : 'Connection lost'}.`);
                if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                    setTimeout(() => {
                        this.reconnectAttempts++;
                        this.initWebSocket();
                        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                    }, this.reconnectDelay);
                }
            };
        } catch (error) {
            console.error("Error initializing WebSocket:", error);
        }
    }
    
    applyInitialState(data) {
        // Don't override local changes if we have them
        if (this.hasLocalChanges) {
            console.log("Local changes exist, not applying initial state");
            return;
        }
        
        // Store this state to avoid echo when we make our first update
        this.lastBroadcastState = {...data};
        
        // Apply the state to the form - similar to handleWebSocketUpdate but resets the form completely
        
        // Update checkboxes
        if (data.checkboxes) {
            // Reset all checkboxes first
            $(".larger-checkbox").prop("checked", false);
            
            for (const id in data.checkboxes) {
                const isChecked = data.checkboxes[id] === true || data.checkboxes[id] === 'true';
                $(`#${id}`).prop("checked", isChecked);
            }
        }
        
        // Update signatures
        if (data.signature1 !== undefined) {
            $("#signature1").val(data.signature1);
            this.drawSignature(data.signature1, document.getElementById("canvas1"));
        }
        
        if (data.signature2 !== undefined) {
            $("#signature2").val(data.signature2);
            this.drawSignature(data.signature2, document.getElementById("canvas2"));
        }
        
        // Update textarea
        if (data.textarea !== undefined) {
            $(".commentary textarea").val(data.textarea);
        }
        
        console.log("Applied initial state from Redis");
    }
    
    handleWebSocketUpdate(data) {
        // Don't apply our own updates to avoid loops
        if (JSON.stringify(data) === JSON.stringify(this.lastBroadcastState)) {
            return;
        }
        
        console.log("Received update from another user:", data);
        
        // Update checkboxes
        if (data.checkboxes) {
            for (const id in data.checkboxes) {
                const isChecked = data.checkboxes[id] === true || data.checkboxes[id] === 'true';
                $(`#${id}`).prop("checked", isChecked);
            }
        }
        
        // Update signatures
        if (data.signature1 !== undefined) {
            $("#signature1").val(data.signature1);
            this.drawSignature(data.signature1, document.getElementById("canvas1"));
        }
        if (data.signature2 !== undefined) {
            $("#signature2").val(data.signature2);
            this.drawSignature(data.signature2, document.getElementById("canvas2"));
        }
        
        // Update textarea
        if (data.textarea !== undefined) {
            $(".commentary textarea").val(data.textarea);
        }
    }
    
    setupSpecSheetPage() {
        // add event listeners to text input fields with debounce
        $("#signature1").on("input", (event) => {
            this.hasLocalChanges = true;
            this.drawSignature($(event.target).val(), document.getElementById("canvas1"));
            this.debounceUpdateState();
        });
    
        $("#signature2").on("input", (event) => {
            this.hasLocalChanges = true;
            this.drawSignature($(event.target).val(), document.getElementById("canvas2"));
            this.debounceUpdateState();
        });

        // add event listeners to checkboxes and update the state
        $(".larger-checkbox").on("click", (event) => {
            this.hasLocalChanges = true;
            this.debounceUpdateState();
        });

        // add event listener to textarea and update the state
        $(".commentary textarea").on("input", (event) => {
            this.hasLocalChanges = true;
            this.debounceUpdateState();
        });
    };
    
    debounceUpdateState() {
        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Set new timer to update after 300ms of inactivity
        this.debounceTimer = setTimeout(() => {
            this.updateServerState();
        }, 300);
    }

    initializeFromStateJson() {
        this.fillFormFromStateJson();
        
        // If we have state from Django's initial rendering, send it to the WebSocket for persistence
        if (this.state_json && Object.keys(this.state_json).length > 0) {
            // Wait a short time to ensure WebSocket connection is established
            setTimeout(() => {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    console.log("Sending initial state from Django template to WebSocket");
                    this.updateServerState();
                } else {
                    console.log("WebSocket not ready, will be sent when state changes");
                }
            }, 1000);
        }
    }    

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie != '') {
            let cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                let cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
            return cookieValue;
        }

    // Add _csrfSafeMethod as a class method
    _csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    // function to draw a signature on a canvas
    drawSignature(signature, canvas) {
        var ctx = canvas.getContext("2d");
        canvas.width = canvas.clientWidth * 2;
        canvas.height = canvas.clientHeight * 2;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.scale(2,2);
        ctx.font = "20px Rage, Lucida Handwriting, cursive";
        ctx.fillText(signature, 5, 18);
      };
  
    // update server state with current state of the page
    updateServerState() {
        // Create the state object from form elements
        const state = {
            checkboxes: {},
            signature1: $("#signature1").val(),
            signature2: $("#signature2").val(),
            textarea: $(".commentary textarea").val(),
        };
        $(".larger-checkbox").each(function() {
            state.checkboxes[$(this).attr("id")] = $(this).is(":checked") ? true : false;
        });
        
        // Store this state to avoid echo
        this.lastBroadcastState = {...state};
        
        // Send via WebSocket if connected
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(state));
        }
                
        $.ajax({
            type: "POST",
            url: window.location.pathname,
            data: JSON.stringify(state, function(key, value) {
                return typeof value === "boolean" ? value.toString() : value}),
            beforeSend: function(xhr, settings) { // ADD beforeSend directly here
                const localCsrftoken = this.getCookie('csrftoken') || 
                    (document.querySelector('meta[name="csrf-token"]') ? document.querySelector('meta[name="csrf-token"]').getAttribute('content') : 
                    (document.querySelector('input[name="csrfmiddlewaretoken"]') ? document.querySelector('input[name="csrfmiddlewaretoken"]').value : ''));
                console.log("AJAX beforeSend - CSRF Token from direct setup:", localCsrftoken); // Diagnostic log
                if (!this._csrfSafeMethod(settings.type) && !settings.crossDomain) { // Use this._csrfSafeMethod
                    xhr.setRequestHeader("X-CSRFToken", localCsrftoken);
                }
            }.bind(this), // Ensure 'this' context is correct for getCookie and _csrfSafeMethod
            success: function() {
                console.log("Updated server state via AJAX");
            },
            error: function(error) {
                console.error("AJAX update failed:", error);
            }
        });
    };

    savePdf() {
        window.jsPDF = window.jspdf.jsPDF;
        const originalSavePdfButton = $('#savePdf');
        originalSavePdfButton.addClass("hidden");
        $('.noPrint').addClass("hidden");
        const mainElement = document.querySelector('[role="main"]');
    
        const removeDynamicUIElements = (specificIds = []) => {
            const idsToRemove = [
                'pdfChoiceContainer',
                'imagePreviewContainer',
                'addMoreImagesBtn',
                'generatePdfBtn',
                'cancelImageUploadBtn',
                'pdfGenError',
                'filenameModalOverlay',
                'pdfDownloadContainer'
            ];
            const allIds = specificIds.length > 0 ? specificIds : idsToRemove;
            allIds.forEach(id => {
                const elem = document.getElementById(id);
                if (elem) elem.remove();
            });
        };
    
        const showOriginalButtonsAndCleanup = () => {
            removeDynamicUIElements();
            originalSavePdfButton.removeClass("hidden");
            $('.noPrint').removeClass("hidden");
        };
        
        const displayPdfDownloadLink = (blobURL, filename, imageDataList = null) => {
            removeDynamicUIElements();
        
            const downloadContainer = document.createElement('div');
            downloadContainer.id = 'pdfDownloadContainer'; 
            downloadContainer.style.marginTop = '20px';
            downloadContainer.style.textAlign = 'center';
            downloadContainer.style.padding = '20px';
            downloadContainer.style.border = '1px solid #ddd';
            downloadContainer.style.borderRadius = '5px';
        
            const title = document.createElement('h5');
            title.textContent = 'Your PDF is Ready';
            title.style.marginBottom = '15px';
        
            const downloadButton = document.createElement('button');
            downloadButton.textContent = `Download ${filename}.pdf`;
            downloadButton.className = 'btn btn-success'; 
            downloadButton.style.marginRight = '10px';
        
            downloadButton.onclick = () => {
                const tempLink = document.createElement('a');
                tempLink.href = blobURL;
                tempLink.setAttribute('download', `${filename}.pdf`);
                tempLink.style.display = 'none';
                document.body.appendChild(tempLink);
                tempLink.click();
                document.body.removeChild(tempLink);
                
                URL.revokeObjectURL(blobURL); 
                if (imageDataList) {
                    imageDataList.forEach(item => URL.revokeObjectURL(item.originalSrc));
                }
                
                removeDynamicUIElements(['pdfDownloadContainer']); 
                showOriginalButtonsAndCleanup(); 
            };
        
            const cancelButton = document.createElement('button');
            cancelButton.textContent = 'Cancel';
            cancelButton.className = 'btn btn-light';
            cancelButton.onclick = () => {
                URL.revokeObjectURL(blobURL); 
                if (imageDataList) {
                    imageDataList.forEach(item => URL.revokeObjectURL(item.originalSrc));
                }
                removeDynamicUIElements(['pdfDownloadContainer']); 
                showOriginalButtonsAndCleanup(); 
            };
        
            downloadContainer.appendChild(title);
            downloadContainer.appendChild(downloadButton);
            downloadContainer.appendChild(cancelButton);
        
            if (mainElement.nextSibling) {
                mainElement.parentNode.insertBefore(downloadContainer, mainElement.nextSibling);
            } else {
                mainElement.parentNode.appendChild(downloadContainer);
            }
            downloadContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        };
    
        const promptForFilenameModal = (defaultFilename, successCallback, cancelCallback) => {
            removeDynamicUIElements(['filenameModalOverlay']);
    
            const overlay = document.createElement('div');
            overlay.id = 'filenameModalOverlay';
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0,0,0,0.5)';
            overlay.style.zIndex = '1000';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
    
            const modal = document.createElement('div');
            modal.id = 'filenameModal';
            modal.style.backgroundColor = 'white';
            modal.style.padding = '20px';
            modal.style.borderRadius = '8px';
            modal.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            modal.style.width = 'clamp(400px, 40vw, 520px)';
            modal.style.maxWidth = '90%';
            modal.style.zIndex = '1001';
    
            const title = document.createElement('h5');
            title.textContent = 'Enter PDF Filename';
            title.style.marginBottom = '15px';
            title.style.textAlign = 'center';
    
            const input = document.createElement('input');
            input.type = 'text';
            input.value = defaultFilename;
            input.style.width = 'calc(100% - 22px)';
            input.style.padding = '10px';
            input.style.marginBottom = '15px';
            input.style.border = '1px solid #ccc';
            input.style.borderRadius = '4px';
    
            const saveButton = document.createElement('button');
            saveButton.textContent = 'Save PDF';
            saveButton.className = 'btn btn-success';
            saveButton.style.marginRight = '10px';
            saveButton.onclick = () => {
                const filename = input.value.trim() || defaultFilename;
                removeDynamicUIElements(['filenameModalOverlay']);
                successCallback(filename);
            };
    
            const cancelButton = document.createElement('button');
            cancelButton.textContent = 'Cancel';
            cancelButton.className = 'btn btn-light';
            cancelButton.onclick = () => {
                removeDynamicUIElements(['filenameModalOverlay']);
                if (cancelCallback) cancelCallback();
            };
            
            overlay.onclick = (event) => {
                if (event.target === overlay) {
                    removeDynamicUIElements(['filenameModalOverlay']);
                    if (cancelCallback) cancelCallback();
                }
            };
    
            modal.appendChild(title);
            modal.appendChild(input);
            const buttonDiv = document.createElement('div');
            buttonDiv.style.textAlign = 'right';
            buttonDiv.appendChild(saveButton);
            buttonDiv.appendChild(cancelButton);
            modal.appendChild(buttonDiv);
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            input.focus();
            input.setSelectionRange(input.value.length, input.value.length);
        };
    
        const handleError = (err, contextMessage) => {
            console.error(contextMessage, err);
            let errorDiv = document.getElementById('pdfGenError');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.id = 'pdfGenError';
                errorDiv.style.color = 'red';
                errorDiv.style.backgroundColor = '#ffe0e0';
                errorDiv.style.padding = '10px';
                errorDiv.style.marginTop = '20px';
                errorDiv.style.border = '1px solid red';
                errorDiv.style.borderRadius = '5px';
                errorDiv.style.textAlign = 'center';
                
                const choiceContainer = document.getElementById('pdfChoiceContainer');
                if (choiceContainer && choiceContainer.parentNode) {
                    choiceContainer.insertAdjacentElement('afterend', errorDiv);
                } else if (mainElement.firstChild) {
                    mainElement.insertBefore(errorDiv, mainElement.firstChild);
                } else {
                    mainElement.appendChild(errorDiv);
                }
            }
            errorDiv.textContent = `Error: ${contextMessage} ${err.message || 'Please try again.'}`;
            errorDiv.style.display = 'block';
        };

        const loadImage = (s) => new Promise((r, j) => { 
            const i = new Image();
            i.onload = () => r(i); 
            i.onerror = j; i.src = s; 
        });

        const toDataURL = (b) => new Promise((r) => {
            const fr = new FileReader(); 
            fr.onload = () => r(fr.result); 
            fr.readAsDataURL(b); 
        });
        
        const base64ToBuf = (d) => {
            const b = (d.split(',')[1] || d),
            n = atob(b), l = n.length,
            a = new ArrayBuffer(l),
            v = new Uint8Array(a);
            for (let i = 0; i < l; i++) v[i] = n.charCodeAt(i);
            return a;
        };
        
        const jpegOrient = (buf) => {
            const v = new DataView(buf);
            if (v.getUint16(0, false) !== 0xffd8) return 1;
            let o = 2,
              L = v.byteLength;
            while (o < L) {
              const m = v.getUint16(o, false);
              o += 2;
              if (m === 0xffe1) {
                o += 2;
                if (v.getUint32(o + 2, false) !== 0x45786966) break;
                const le = v.getUint16(o + 8, false) === 0x4949;
                const ifd = v.getUint32(o + 4, le);
                o += 10 + ifd;
                const n = v.getUint16(o, le);
                o += 2;
                for (let i = 0; i < n; i++) {
                  const p = o + i * 12;
                  if (v.getUint16(p, le) === 0x0112) return v.getUint16(p + 8, le);
                }
              } else if ((m & 0xff00) !== 0xff00) break;
              else o += v.getUint16(o, false);
            }
            return 1;
        };


        const SCREEN_QUAL = 0.8, MAX_SIDE = 1080, MAX_IMG_BYTES = 1 * 1024 * 1024;

        const hasAlpha = (ctx, w, h) => {
            const d = ctx.getImageData(0, 0, w, h).data;
            for (let i = 3; i < d.length; i += 4) if (d[i] !== 255) return true;
            return false;
        };
        
        const normalizeImage = async (src) => {
            let dataURL, isJpeg = false, buf=null;
            if (src instanceof Blob){ dataURL = await toDataURL(src); isJpeg = src.type==='image/jpeg'; if(isJpeg) buf = await src.arrayBuffer(); }
            else { dataURL = src; isJpeg = /^data:image\/jpeg/.test(src); if(isJpeg) buf = base64ToBuf(src); }
        
            const orient = isJpeg ? jpegOrient(buf) : 1;
            const img = await loadImage(dataURL);
            let w = img.naturalWidth, h = img.naturalHeight;
            const c = document.createElement('canvas'), ctx = c.getContext('2d');
            switch(orient){case 3:c.width=w;c.height=h;ctx.translate(w,h);ctx.rotate(Math.PI);break;
                case 6:c.width=h;c.height=w;ctx.translate(h,0);ctx.rotate(Math.PI/2);[w,h]=[h,w];break;
                case 8:c.width=h;c.height=w;ctx.translate(0,w);ctx.rotate(-Math.PI/2);[w,h]=[h,w];break;
                default:c.width=w;c.height=h;}
            ctx.drawImage(img,0,0);
        
            const maxSide = Math.max(c.width,c.height);
            if(maxSide>MAX_SIDE){
                const s=MAX_SIDE/maxSide, nw=Math.round(c.width*s), nh=Math.round(c.height*s);
                const r=document.createElement('canvas'), rx=r.getContext('2d');
                r.width=nw; r.height=nh; rx.drawImage(c,0,0,nw,nh);
                c.width=nw; c.height=nh; ctx.clearRect(0,0,nw,nh); ctx.drawImage(r,0,0);
            }
        
            let fmt='PNG', outURL;
            if(!hasAlpha(ctx,c.width,c.height)){
                let q=0.75;
                do{ outURL=c.toDataURL('image/jpeg',q); const b=(outURL.length-outURL.indexOf(',')-1)*0.75;
                    if(b<=MAX_IMG_BYTES||q<=0.3)break; q-=0.1;}while(true);
                fmt='JPEG';
            }else{ outURL=c.toDataURL('image/png'); }
        
            return{src:outURL,width:c.width,height:c.height,fmt};
        };
        
        const generatePdf = async (filename, imageDataList=[]) => {
            try{
                const cap = await html2canvas(mainElement,{scale:1});
                const cw=mainElement.offsetWidth, ch=mainElement.offsetHeight, ori=cw>=ch?'l':'p';
                const pdf=new jsPDF({orientation:ori,unit:'px',compressPdf:true});
                pdf.internal.pageSize.width=cw; pdf.internal.pageSize.height=ch;
                pdf.addImage(cap.toDataURL('image/jpeg',SCREEN_QUAL),'JPEG',0,0,cw,ch);
        
                const norm=await Promise.all(imageDataList.map(({originalSrc})=>normalizeImage(originalSrc)));
                for(const n of norm){
                    const pOri=n.width>=n.height?'l':'p';
                    pdf.addPage([n.width,n.height],pOri);
                    const pw=pdf.internal.pageSize.getWidth(), ph=pdf.internal.pageSize.getHeight();
                    const s=Math.min(pw/n.width,ph/n.height);
                    const dw=n.width*s, dh=n.height*s, x=(pw-dw)/2, y=(ph-dh)/2;
                    pdf.addImage(n.src,n.fmt,x,y,dw,dh);
                }
                displayPdfDownloadLink(URL.createObjectURL(pdf.output('blob')),filename,imageDataList);
            }catch(e){handleError(e,'Generating PDF failed.');showOriginalButtonsAndCleanup();}
        };
        
        
        const generatePdfWithoutImages = async () => {
            removeDynamicUIElements(['pdfChoiceContainer']);
    
            let defaultFilename = 'SpecSheet';
            try {
                const itemCodeInput = document.getElementById('itemcode').textContent;
                if (itemCodeInput && itemCodeInput.trim() !== '') {
                    defaultFilename = itemCodeInput.trim() + " ";
                }
            } catch (e) {
                console.warn("Could not find or access item code for default filename.", e);
            }
    
            promptForFilenameModal(defaultFilename, (filename) => {
                generatePdf(filename, []);
            }, () => {
                showOriginalButtonsAndCleanup();
            });
        };
    
        const startImageUploadProcess = () => {
            removeDynamicUIElements(['pdfChoiceContainer']);
    
            const previewContainer = document.createElement('div');
            previewContainer.id = 'imagePreviewContainer';
            previewContainer.style.display = 'flex';
            previewContainer.style.flexWrap = 'wrap';
            previewContainer.style.marginTop = '20px';
            previewContainer.style.border = '1px dashed #ccc';
            previewContainer.style.padding = '10px';
            previewContainer.style.minHeight = '100px';
    
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.accept = 'image/tiff, image/jfif, image/jpeg, image/jpg, image/png, image/gif, image/bmp, image/webp, image/heic, image/heif';
            
            const imageDataList = [];
    
            const updateGeneratePdfButtonState = () => {
                const generateBtn = document.getElementById('generatePdfBtn');
                if (generateBtn) {
                    generateBtn.disabled = imageDataList.length === 0;
                }
            };
    
            input.onchange = async (event) => {
                const files = event.target.files;
                if (!files.length) return;
    
                const processingMessage = document.createElement('p');
                processingMessage.id = 'processingImagesMsg';
                processingMessage.textContent = 'Processing images...';
                previewContainer.appendChild(processingMessage);
    
                for (const file of files) {
                    let inputFile = file;
                    if (file.name.toLowerCase().endsWith('.heic') || file.name.toLowerCase().endsWith('.heif')) {
                         try {
                            const heicBlob = new Blob([file], { type: 'image/heic' });
                            const pngBlob = await heic2any({
                                blob: heicBlob,
                                toType: 'image/png',
                                quality: 0.9,
                            });
                            inputFile = new File([pngBlob], file.name.replace(/\.(heic|heif)$/i, '.png'), { type: 'image/png' });
                        } catch (heicError) {
                            handleError(heicError, `Could not convert HEIC image: ${file.name}.`);
                            if(document.getElementById('processingImagesMsg')) document.getElementById('processingImagesMsg').remove();
                            return;
                        }
                    }
                    
                    const img = new Image();
                    const objectURL = URL.createObjectURL(inputFile);
                    img.src = objectURL;
    
                    const previewDiv = document.createElement('div');
                    previewDiv.style.position = 'relative';
                    previewDiv.style.margin = '10px';
                    previewDiv.style.border = '1px solid #eee';
                    previewDiv.style.padding = '5px';
    
                    const removeBtn = document.createElement('button');
                    removeBtn.textContent = 'X';
                    removeBtn.style.position = 'absolute';
                    removeBtn.style.right = '0';
                    removeBtn.style.top = '0';
                    removeBtn.style.zIndex = '10';
                    removeBtn.style.background = 'rgba(255,0,0,0.7)';
                    removeBtn.style.color = 'white';
                    removeBtn.style.border = 'none';
                    removeBtn.style.cursor = 'pointer';
    
                    removeBtn.onclick = () => {
                        previewDiv.remove();
                        const dataIndex = imageDataList.findIndex(item => item.originalSrc === objectURL);
                        if (dataIndex !== -1) {
                            imageDataList.splice(dataIndex, 1);
                        }
                        URL.revokeObjectURL(objectURL);
                        updateGeneratePdfButtonState();
                    };
                    
                    const canvas = document.createElement('canvas');
                    canvas.width = 150;
                    canvas.height = 150;
                    const ctx = canvas.getContext('2d');
    
                    try {
                        await new Promise((resolve, reject) => {
                            img.onload = () => {
                                const width = img.width;
                                const height = img.height;
                                const size = Math.min(width, height);
                                const x = (width - size) / 2;
                                const y = (height - size) / 2;
                                ctx.drawImage(img, x, y, size, size, 0, 0, canvas.width, canvas.height);
                                
                                const currentImageData = {
                                    originalFile: inputFile,
                                    originalSrc: objectURL,
                                    width: width,
                                    height: height,
                                    previewSrc: canvas.toDataURL(),
                                    exifOrientation: 1
                                };
                                imageDataList.push(currentImageData);
    
                                EXIF.getData(inputFile, function() {
                                    currentImageData.exifOrientation = EXIF.getTag(this, 'Orientation') || 1;
                                    resolve();
                                });
                            };
                            img.onerror = (err) => {
                                reject(new Error(`Could not load image: ${inputFile.name}`));
                            };
                        });
                    } catch (loadError) {
                        handleError(loadError, "Failed to load image for preview.");
                        previewDiv.remove();
                        URL.revokeObjectURL(objectURL);
                        if(document.getElementById('processingImagesMsg')) document.getElementById('processingImagesMsg').remove();
                        return;
                    }
    
                    previewDiv.appendChild(removeBtn);
                    previewDiv.appendChild(canvas);
                    previewContainer.appendChild(previewDiv);
                }
                if(document.getElementById('processingImagesMsg')) document.getElementById('processingImagesMsg').remove();
                updateGeneratePdfButtonState();
            };
    
            const addMoreImagesBtn = document.createElement('button');
            addMoreImagesBtn.id = 'addMoreImagesBtn';
            addMoreImagesBtn.textContent = 'Add/Change Images';
            addMoreImagesBtn.className = 'btn btn-info';
            addMoreImagesBtn.style.marginRight = '10px';
            addMoreImagesBtn.onclick = () => input.click();
    
            const generatePdfBtn = document.createElement('button');
            generatePdfBtn.id = 'generatePdfBtn';
            generatePdfBtn.textContent = 'Generate PDF with Images';
            generatePdfBtn.className = 'btn btn-success';
            generatePdfBtn.style.marginRight = '10px';
            generatePdfBtn.disabled = true;
    
            generatePdfBtn.onclick = async () => {
                if (imageDataList.length === 0) {
                    handleError(new Error("No images selected."), "Cannot generate PDF.");
                    return;
                }
                
                removeDynamicUIElements(['addMoreImagesBtn', 'generatePdfBtn', 'cancelImageUploadBtn']);
    
                let defaultFilename = 'SpecSheet_WithImages';
                try {
                    const itemCodeInput = document.getElementById('itemcode').textContent;
                    if (itemCodeInput && itemCodeInput.trim() !== '') {
                        defaultFilename = itemCodeInput.trim() + " ";
                    }
                } catch (e) {
                    console.warn("Could not find or access item code for default filename (with images).", e);
                }
    
                promptForFilenameModal(defaultFilename, (filename) => {
                    generatePdf(filename, imageDataList);
                }, () => {
                    showOriginalButtonsAndCleanup();
                });
            };
    
            const cancelImageUploadBtn = document.createElement('button');
            cancelImageUploadBtn.id = 'cancelImageUploadBtn';
            cancelImageUploadBtn.textContent = 'Cancel';
            cancelImageUploadBtn.className = 'btn btn-danger';
            cancelImageUploadBtn.onclick = () => {
                imageDataList.forEach(item => URL.revokeObjectURL(item.originalSrc));
                showOriginalButtonsAndCleanup();
            };
            
            const buttonContainer = document.createElement('div');
            buttonContainer.style.marginTop = '10px';
            buttonContainer.appendChild(addMoreImagesBtn);
            buttonContainer.appendChild(generatePdfBtn);
            buttonContainer.appendChild(cancelImageUploadBtn);
    
            mainElement.appendChild(previewContainer);
            mainElement.appendChild(buttonContainer);
            
            input.click();
        };
    
        const choiceContainer = document.createElement('div');
        choiceContainer.id = 'pdfChoiceContainer';
        choiceContainer.style.marginTop = '20px';
        choiceContainer.style.textAlign = 'center';
        choiceContainer.style.padding = '20px';
        choiceContainer.style.border = '1px solid #ddd';
        choiceContainer.style.borderRadius = '5px';
    
        const title = document.createElement('h4');
        title.textContent = 'Create PDF Version';
        title.style.marginBottom = '15px';
    
        const btnSaveSimple = document.createElement('button');
        btnSaveSimple.textContent = 'Save PDF (No Images)';
        btnSaveSimple.className = 'btn btn-primary';
        btnSaveSimple.style.marginRight = '10px';
        btnSaveSimple.onclick = generatePdfWithoutImages;
    
        const btnSaveWithImages = document.createElement('button');
        btnSaveWithImages.textContent = 'Add Images & Save PDF';
        btnSaveWithImages.className = 'btn btn-success';
        btnSaveWithImages.onclick = startImageUploadProcess;
    
        const btnCancelChoice = document.createElement('button');
        btnCancelChoice.textContent = 'Cancel';
        btnCancelChoice.className = 'btn btn-light';
        btnCancelChoice.style.marginLeft = '10px';
        btnCancelChoice.onclick = showOriginalButtonsAndCleanup;
    
        choiceContainer.appendChild(title);
        choiceContainer.appendChild(btnSaveSimple);
        choiceContainer.appendChild(btnSaveWithImages);
        choiceContainer.appendChild(btnCancelChoice);
        
        if (mainElement.nextSibling) {
            mainElement.parentNode.insertBefore(choiceContainer, mainElement.nextSibling);
        } else {
            mainElement.parentNode.appendChild(choiceContainer);
        }
        choiceContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    fillFormFromStateJson() {
        if (this.state_json) {
            // this.hasLocalChanges = true; // This line is removed
            
            const checkboxes = this.state_json.checkboxes;
            if (checkboxes) { // Check if the checkboxes property exists
                for (const id in checkboxes) {
                    const val = checkboxes[id];
                    // Use a consistent check for boolean true or string 'true'
                    const isChecked = val === true || val === 'true'; 
                    $(`#${id}`).prop("checked", isChecked);
                }
            }
            $("#signature1").val(this.state_json.signature1 || ''); // Ensure undefined becomes empty string
            $("#signature2").val(this.state_json.signature2 || ''); // Ensure undefined becomes empty string
            $(".commentary textarea").val(this.state_json.textarea || ''); // Ensure undefined becomes empty string
    
            if (this.state_json.signature1) {
                this.drawSignature(this.state_json.signature1, document.getElementById("canvas1"));
            }
            if (this.state_json.signature2) {
                this.drawSignature(this.state_json.signature2, document.getElementById("canvas2"));
            }
        }
    };

    populatePrintDate() {
        const printDate = new Date().toLocaleDateString();
        $("#printDate").text("Printed on: " + printDate);
    }
    
};