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
        // const staticpath = "/static/static/prodverse/html/Kinpak%2C%20Inc/Production%20-%20Web%20Parts/";
        const staticpath = "/dynamic/html/"

         // Function to append a random string to the HTML file name
        function appendCacheBusting(file) {
            const uniqueid = new Date().getTime();
            const parts = file
            return parts + '?v=' + uniqueid;
        }

        // Load Horix schedule as default
        let filePath = staticpath + "inlineschedule.html"
        let fileBusted = appendCacheBusting(filePath)
        $(includes).load(fileBusted, function() {
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
                let file = staticpath + `${buttonId.replace('button', 'schedule')}.html`;
                fileBusted = appendCacheBusting(file)
                console.log(fileBusted);
                // Load schedule file and then execute customizations
                $(this).load(fileBusted, function() {
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
                    <li><a class="dropdown-item" href="/prodverse/spec-sheet/${encodeURIComponent(itemCode)}" target="blank">
                    Spec Sheet
                    </a></li>
                    <li><a class="dropdown-item" href="/prodverse/pick-ticket/${encodeURIComponent(itemCode)}?schedule-quantity=${encodeURIComponent(qty)}" target="blank">
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

export class SpecSheetPage {
    constructor() {
        try {
            this.setupSpecSheetPage();
            this.drawSignature = this.drawSignature.bind(this);
            this.savePdf = this.savePdf.bind(this);
            console.log("Instance of class SpecSheetPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };
    
    setupSpecSheetPage() {
        // add event listeners to text input fields
        $("#signature1").on("input", (event) => {
            this.drawSignature($(event.target).val(), document.getElementById("canvas1"));
        });
    
        $("#signature2").on("input", (event) => {
            this.drawSignature($(event.target).val(), document.getElementById("canvas2"));
        });
    
        // add event listener to the Save PDF button
        $("#savePdf").on("click", this.savePdf);
    };

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
  
    // function to save the current page as a PDF
    savePdf() {
        window.jsPDF = window.jspdf.jsPDF;
        $('#savePdf').addClass("hidden");
        const mainElement = document.querySelector('[role="main"]');
        html2canvas(mainElement,{scale: 2}).then((canvas) => {
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
            pdf.save('RENAMEFILE.pdf');
        });
        $('#savePdf').removeClass("hidden");
    };

};