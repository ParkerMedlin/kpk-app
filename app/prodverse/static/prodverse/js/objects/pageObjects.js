export class ProductionSchedulePage {
    constructor() {
        try {
            this.getJulianDate = this.getJulianDate.bind(this)
            this.addItemCodeLinks = this.addItemCodeLinks.bind(this);
            this.getTextNodes = this.getTextNodes.bind(this);
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
    }; 

    addItemCodeLinks() {
        const tableRows = Array.from(document.querySelectorAll('table tr'));
        const getJulianDate = this.getJulianDate;
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
        const poNumbers = Array.from(document.querySelectorAll('td:nth-child(4)'));

        cells.forEach((cell, index) => {
            const text = cell.textContent.trim();
            if (text.length > 0 && !text.includes(' ') && text !== "P/N") {
                const itemCode = text;
                const qty = parseInt(cell.parentElement.querySelector(`td:nth-child(${qtyIndex})`).textContent.trim().replace(',', ''), 10);
                const poNumber = poNumbers[index].textContent.trim();
                const julianDate = getJulianDate();
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
                    </ul>
                    </div>
                
            `;
            cell.innerHTML = dropdownHTML;
            cell.style.cursor = "pointer";
            }
        });
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

};

export class SpecSheetPage {
    constructor() {
        try {
            this.setupSpecSheetPage();
            this.state_json = JSON.parse($("#state_json").text().replaceAll("'",'"'));
            this.drawSignature = this.drawSignature.bind(this);
            this.savePdf = this.savePdf.bind(this);
            console.log("Instance of class SpecSheetPage created.");
            this.initializeFromStateJson();
            $("#savePdf").on("click", this.savePdf);
        } catch(err) {
            console.error(err.message);
        };
    };
    
    setupSpecSheetPage() {
        // add event listeners to text input fields
        $("#signature1").on("input", (event) => {
            this.drawSignature($(event.target).val(), document.getElementById("canvas1"));
            this.updateServerState();
        });
    
        $("#signature2").on("input", (event) => {
            this.drawSignature($(event.target).val(), document.getElementById("canvas2"));
            this.updateServerState();
        });

        // add event listeners to checkboxes and update the state
        $(".larger-checkbox").on("click", (event) => {
            this.updateServerState();
        });

        // add event listener to textarea and update the state
        $(".commentary textarea").on("input", (event) => {
            this.updateServerState();
        });
    };

    initializeFromStateJson() {
        this.fillFormFromStateJson();
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
        const csrftoken = this.getCookie('csrftoken');
        const state = {
            checkboxes: {},
            signature1: $("#signature1").val(),
            signature2: $("#signature2").val(),
            textarea: $(".commentary textarea").val(),
        };
        $(".larger-checkbox").each(function() {
            state.checkboxes[$(this).attr("id")] = $(this).is(":checked") ? true : false;
        });
                
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
                console.log("Updated server state");
                console.log(JSON.stringify(state, function(key, value) {
                    return typeof value === "boolean" ? value.toString() : value;
                }));
            },
            error: function(error) {
                console.error(error);
            }
        });
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

    fillFormFromStateJson() {
        if (this.state_json) {
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