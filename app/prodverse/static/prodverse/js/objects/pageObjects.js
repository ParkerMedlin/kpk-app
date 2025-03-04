import { CreateBlendLabelButton } from '../objects/buttonObjects.js'
import { getBlendQuantitiesPerBill, getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'


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
            console.log("Instance of class ProductionSchedulePage created.");
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
            'kitschedule.html': this.removeColumns(6),
            'oilschedule.html': this.removeColumns(6)
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
                    // const div = document.createElement('div');
                    // div.id = 'Harvey';
                    // // img.src = '/static/static/core/media/kevin-gates-rbs-intro.gif'; // Adjust the path as necessary
                    // div.style.position = 'fixed';
                    // div.style.backgroundColor = 'black';
                    // div.style.top = '0';
                    // div.style.left = '0';
                    // div.style.width = '100%';
                    // div.style.height = '100%';
                    // div.style.zIndex = '1000';
                    // div.style.opacity = '50%';
                    // document.body.appendChild(div);
                    
                    
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

        const blendQuantitiesPerBill = getBlendQuantitiesPerBill();
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
            const blendQuantity = quantity * qtyPerBill
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
                        </ul>
                    </div>
                `;
            cell.innerHTML = dropdownHTML;
            cell.style.cursor = "pointer";
            // <li><a class="dropdown-item issueSheetLink" 
            //                 href="/core/display-this-issue-sheet/${encodeURIComponent(prodLine)}/${encodeURIComponent(itemCode)}?runDate=${runDate}&totalGal=${blendQuantity}"
            //                 data-prodLine=""
            //                 target="blank">
            //             Issue Sheet
            //             </a></li>
            //             <li><a class="dropdown-item blendLotNumbersLink" 
            //                 href="/core/get-json-matching-lot-numbers?prodLine=${encodeURIComponent(prodLine)}&itemCode=${encodedItemCode}&runDate=${runDate}&totalGal=${blendQuantity}"
            //                 data-encodedItemCode="${encodedItemCode}"
            //                 target="blank">
            //             Lot Numbers
            //             </a></li>
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
            this.socket = null;
            this.hasLocalChanges = false;
            this.debounceTimer = null;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
            this.reconnectDelay = 3000; // 3 seconds
            
            this.spec_id = this.extractSpecIdFromUrl();
            console.log("Spec ID initialized in constructor:", this.spec_id);
            
            this.state_json = null;
            this.lastBroadcastState = null; // Track last broadcasted state to avoid loops
            this.setupSpecSheetPage();
            this.drawSignature = this.drawSignature.bind(this);
            this.savePdf = this.savePdf.bind(this);
            this.initWebSocket = this.initWebSocket.bind(this);
            this.updateServerState = this.updateServerState.bind(this);
            this.initWebSocket();
            console.log("Instance of class SpecSheetPage created.");
            this.initializeFromStateJson();
            $("#savePdf").on("click", this.savePdf);
            $("#signature1").drawSignature(this.val(), document.getElementById("canvas1"));
            $("#signature2").drawSignature(this.val(), document.getElementById("canvas2"));
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
                
        // Also send to server via AJAX for persistence
        const csrftoken = this.getCookie('csrftoken');
        
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        };

        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            }
        });

        $.ajax({
            type: "POST",
            url: window.location.pathname,
            data: JSON.stringify(state, function(key, value) {
                return typeof value === "boolean" ? value.toString() : value}),
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
        $('#savePdf').addClass("hidden");
        $('.noPrint').addClass("hidden");
        const mainElement = document.querySelector('[role="main"]');
    
        // Prompt the user if they want to upload images
        const userResponse = confirm("Would you like to upload images?");

        if (userResponse) {          
            // Create a container for image previews
            const previewContainer = document.createElement('div');
            previewContainer.style.display = 'flex';
            previewContainer.style.flexWrap = 'wrap';
            previewContainer.style.marginTop = '20px';
            
            // Allow the user to select multiple images
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.accept = 'image/tiff, image/jfif, image/jpeg, image/png, image/gif, image/bmp, image/webp, image/heic, image/heif';
            
            // Create an array to store the image data
            const imageDataList = [];

            // Process the selected images
            input.onchange = async (event) => {
                const files = event.target.files;
            
                for (const file of files) {
                    let inputFile = file;
                    if (file.name.toLowerCase().endsWith('.heic')) {
                        const newBlob = new Blob([file], { type: 'image/heic' });
                        inputFile = new File([newBlob], file.name, { type: 'image/heic' });
                    };
                    
                    const isHeic = inputFile.type === 'image/heic' || inputFile.type === 'image/heif';
                    
                    if (isHeic) {
                        // Convert HEIC image to a Blob of type 'image/png'
                        const pngBlob = await heic2any({
                            blob: inputFile,
                            toType: 'image/png',
                            quality: 1, // Quality setting between 0 and 1 (1 for highest quality)
                      });
                    
                    // Create a new File object from the Blob
                    const pngFile = new File([pngBlob], file.name.replace(/\.(heic|heif)$/i, '.png'), {
                        type: 'image/png',
                    });
                
                    // Replace the HEIC file with the converted PNG file
                    inputFile = pngFile;
                    };
                
                    const img = new Image();
                    img.src = URL.createObjectURL(inputFile);

                    // Read the EXIF orientation data
                    EXIF.getData(file, function() {
                        const orientation = EXIF.getTag(this, 'Orientation') || 1;
                        const index = imageDataList.findIndex((imgData) => imgData.originalSrc === img.src);
                        if (index !== -1) {
                            imageDataList[index].exifOrientation = orientation;
                        }
                    });
                
                    // Create a div for each image preview
                    const previewDiv = document.createElement('div');
                    previewDiv.style.position = 'relative';
                    previewDiv.style.margin = '10px';
                
                    // Create a remove button for each image
                    const removeBtn = document.createElement('button');
                    removeBtn.textContent = 'X';
                    removeBtn.style.position = 'absolute';
                    removeBtn.style.right = '0';
                    removeBtn.style.top = '0';
                    removeBtn.style.zIndex = '10';
                    removeBtn.onclick = () => {
                        previewDiv.remove();
                        const index = imageDataList.findIndex((imgData) => imgData.previewSrc === canvas.toDataURL());
                        imageDataList.splice(index, 1);

                        // Check if all images are removed from the preview container
                        if (imageDataList.length === 0) {
                            // Hide the Generate PDF button and show the Save PDF button
                            generatePdfBtn.style.display = 'none';
                            addMoreImagesBtn.style.display ='none';
                            $('#savePdf').removeClass("hidden");
                        }
                    };
                    
                    // Create a canvas for each image preview
                    const canvas = document.createElement('canvas');
                    canvas.width = 200;
                    canvas.height = 200;
                    const ctx = canvas.getContext('2d');

                    // Draw the image on the canvas with a 200x200px square preview
                    await new Promise((resolve) => {
                        img.onload = () => {
                            const width = img.width;
                            const height = img.height;
                            const size = Math.min(width, height);
                            const x = (width - size) / 2;
                            const y = (height - size) / 2;
                            ctx.drawImage(img, x, y, size, size, 0, 0, 200, 200);
                            imageDataList.push({
                                originalSrc: img.src,
                                width: width,
                                height: height,
                                previewSrc: canvas.toDataURL(),
                            });
                            resolve();
                        };
                    });


                    // Add the image and remove button to the preview div
                    previewDiv.appendChild(removeBtn);
                    previewDiv.appendChild(canvas);
                    previewContainer.appendChild(previewDiv);
                
                };
            };

            // Create an 'Add more images' button
            const addMoreImagesBtn = document.createElement('button');
            addMoreImagesBtn.textContent = 'Add more images';
            addMoreImagesBtn.onclick = () => {
                input.click();
            };

            // Create a 'Generate PDF' button
            const generatePdfBtn = document.createElement('button');
            generatePdfBtn.textContent = 'Generate PDF';
            generatePdfBtn.onclick = async () => {
                // Hide the button and preview container
                generatePdfBtn.style.display = 'none';
                addMoreImagesBtn.style.display ='none';
                previewContainer.style.display = 'none';

                await html2canvas(mainElement, { scale: 2 }).then(async (canvas) => {
                    const componentWidth = mainElement.offsetWidth;
                    const componentHeight = mainElement.offsetHeight;
                
                    const orientation = componentWidth >= componentHeight ? 'l' : 'p';
                
                    const imgData = canvas.toDataURL('image/png');
                    const pdf = new jsPDF({
                        orientation,
                        unit: 'px'
                    });
                
                    pdf.internal.pageSize.width = componentWidth;
                    pdf.internal.pageSize.height = componentHeight;
                
                    pdf.addImage(imgData, 'PNG', 0, 0, componentWidth, componentHeight);
                
                    for (const imgData of imageDataList) {
                        const { originalSrc, width, height, exifOrientation } = imgData;
                        
                        // Calculate the rotation angle based on the EXIF orientation
                        let angle = 0;
                        if (exifOrientation === 6) {
                            angle = 90;
                        } else if (exifOrientation === 3) {
                            angle = 180;
                        } else if (exifOrientation === 8) {
                            angle = 270;
                        }

                        // Calculate the scale to fit the image on the page
                        const scaleX = pdf.internal.pageSize.width / width;
                        const scaleY = pdf.internal.pageSize.height / height;
                        const scale = Math.min(scaleX, scaleY);
                                            
                        // Determine the orientation based on the image dimensions
                        const orientation = width >= height ? 'l' : 'p';
                                            
                        // Add a new page with the correct orientation
                        pdf.addPage(orientation);
                                            
                        // Set the page width and height
                        const pageWidth = orientation === 'l' ? Math.max(width, height) : Math.min(width, height);
                        const pageHeight = orientation === 'l' ? Math.min(width, height) : Math.max(width, height);
                        pdf.internal.pageSize.setWidth(pageWidth);
                        pdf.internal.pageSize.setHeight(pageHeight);
                                            
                        // Add the image to the page using the calculated scale
                        const imgWidth = width;
                        const imgHeight = height;
                        const posX = (pageWidth - imgWidth) / 2;
                        const posY = (pageHeight - imgHeight) / 2;
                        pdf.addImage({
                            imageData: originalSrc,
                            format: 'PNG',
                            x: posX,
                            y: posY,
                            w: imgWidth,
                            h: imgHeight,
                            angle: angle,
                            rotationCenterX: posX + imgWidth / 2,
                            rotationCenterY: posY + imgHeight / 2,
                        });
                    }
                
                    // Save the final PDF
                    const defaultFilename = 'RENAMEFILE';
                    const filename = prompt('Please enter a filename:', defaultFilename) || defaultFilename;
                    pdf.save(`${filename}.pdf`);

                    // Show the button and preview container again
                    generatePdfBtn.style.display = '';
                    previewContainer.style.display = 'flex';
                });
            };
        
            // Add the 'Generate PDF' button and preview container to the page
            mainElement.appendChild(previewContainer);
            if (!mainElement.contains(addMoreImagesBtn)) {
                mainElement.appendChild(addMoreImagesBtn);
            };
            if (!mainElement.contains(generatePdfBtn)) {
                mainElement.appendChild(generatePdfBtn);
            };

            input.click();

        } else {
            // Generate PDF without images
            const generatePdf = async () => {
                await html2canvas(mainElement, { scale: 2 }).then(async (canvas) => {
                    const componentWidth = mainElement.offsetWidth;
                    const componentHeight = mainElement.offsetHeight;

                    const orientation = componentWidth >= componentHeight ? 'l' : 'p';

                    const imgData = canvas.toDataURL('image/png');
                    const pdf = new jsPDF({
                        orientation,
                        unit: 'px'
                    });

                    pdf.internal.pageSize.width = componentWidth;
                    pdf.internal.pageSize.height = componentHeight;

                    pdf.addImage(imgData, 'PNG', 0, 0, componentWidth, componentHeight);

                    // Save the final PDF
                    const defaultFilename = 'RENAMEFILE';
                    const filename = prompt('Please enter a filename:', defaultFilename) || defaultFilename;
                    pdf.save(`${filename}.pdf`);

                    $('#savePdf').removeClass("hidden");
                });
            };

            generatePdf();
        }
        $('.noPrint').removeClass("hidden");
    };
        


    fillFormFromStateJson() {
        if (this.state_json) {
            // Mark that we have local changes to avoid overriding with initial state
            this.hasLocalChanges = true;
            
            const checkboxes = this.state_json.checkboxes;
            for (const id in checkboxes) {
                const isChecked = checkboxes[id] === 'true' ? true : false;
                $(`#${id}`).prop("checked", isChecked);
            }
            $("#signature1").val(this.state_json.signature1);
            $("#signature2").val(this.state_json.signature2);
            $(".commentary textarea").val(this.state_json.textarea);
    
            if (this.state_json.signature1) {
                this.drawSignature(this.state_json.signature1, document.getElementById("canvas1"));
            }
            if (this.state_json.signature2) {
                this.drawSignature(this.state_json.signature2, document.getElementById("canvas2"));
            }
        }
    };
    
};