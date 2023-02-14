export class ProductionSchedulePage {
    constructor() {
        try {
            this.setupProductionSchedule();
            console.log("Instance of class ProductionSchedulePage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupProductionSchedule(){
        const addItemCodeLinks = this.addItemCodeLinks;
        const getTextNodes = this.getTextNodes;
        var includes = $('[data-include]');
        const staticpath = "\\static\\static\\prodverse\\html\\Kinpak,%20Inc\\Production%20-%20Web%20Parts\\";
        // Load Horix schedule as default
        $(includes).load(staticpath + "inlineschedule.html", function() {
        // Get all the text nodes in the page
        const textNodes = getTextNodes();
        // Iterate through the text nodes and remove non-ASCII characters
        textNodes.forEach(node => {
            node.nodeValue = node.nodeValue.replace(/[^\x00-\x7F]/g, "");
        });
        // Link to Specsheet
        addItemCodeLinks()
        });
        // Put buttons in array
        const scheduleButtons = ['horixbutton', 'inlinebutton', 'blisterbutton', 'pdbutton', 'jbbutton', 'oilbutton', 'kitbutton'];
        scheduleButtons.forEach(buttonId => {
        $.each(includes, function () {
            $(`#${buttonId}`).click(() => {  
            var file = staticpath + `${buttonId.replace('button', 'schedule')}.html`;
            console.log(file);
            // Load schedule file and then execute customizations
            $(this).load(file, function() {
                //Customize appearance
                // Get all the text nodes in the page
                const textNodes = getTextNodes();
                // Iterate through the text nodes and remove non-ASCII characters
                textNodes.forEach(node => {
                    node.nodeValue = node.nodeValue.replace(/[^\x00-\x7F]/g, "");
                });
                
                // Unhide truncated text
                const spans = document.querySelectorAll('table span');
                spans.forEach(span => {
                    span.style.display = '';
                });

                // Blister Schedule Customizations
                if (file === staticpath + 'blisterschedule.html') {
                    // Hide blend, bottle, and cap columns
                    $('td:nth-child(10)').remove();
                    $('td:nth-child(9)').remove();
                    $('td:nth-child(6)').remove();
                };
                
                // Kit + Oil Schedule Remove Blend Column
                if (file === staticpath + 'kitschedule.html' || file === staticpath + 'oilschedule.html') {
                    $('td:nth-child(6)').remove();
                };
                
                // Link to Specsheet
                addItemCodeLinks()
            });
            });
        });
        });
    }

    addItemCodeLinks() {
        const tableRows = Array.from(document.querySelectorAll('table tr'));
        let qtyIndex;
        
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
        
        const cells = Array.from(document.querySelectorAll('td:nth-child(3)'));
        cells.forEach(cell => {
            const text = cell.textContent.trim();
            if (text.length > 0 && !text.includes(' ') && text !== "P/N") {
            const itemCode = text;
            const qty = parseInt(cell.parentElement.querySelector(`td:nth-child(${qtyIndex})`).textContent.trim().replace(',', ''), 10);
            const dropdownHTML = `
                <div class="dropdown">
                <a class="dropdown-toggle itemCodeDropdownLink" type="button" data-bs-toggle="dropdown">${itemCode}</a>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="/prodverse/specsheet/${encodeURIComponent(itemCode)}" target="blank">
                    Spec Sheet
                    </a></li>
                    <li><a class="dropdown-item" href="/prodverse/pickticket/${encodeURIComponent(itemCode)}?schedule_qty=${encodeURIComponent(qty)}" target="blank">
                    Pick Ticket
                    </a></li>
                </ul>
                </div>
                
            `;
            cell.innerHTML = dropdownHTML;
            cell.style.cursor = "pointer";
            }
        });
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

};