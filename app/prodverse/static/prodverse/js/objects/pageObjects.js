import { CreateBlendLabelButton } from '../objects/buttonObjects.js'
import { getBlendQuantitiesPerBill, getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'


export class ProductionSchedulePage {
    constructor() {
        try {
            this.getJulianDate = this.getJulianDate.bind(this)
            this.addItemCodeLinks = this.addItemCodeLinks.bind(this);
            this.getTextNodes = this.getTextNodes.bind(this);
            this.unhideTruncatedText = this.unhideTruncatedText.bind(this);
            this.setupProductionSchedule();
            console.log("Instance of class ProductionSchedulePage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupProductionSchedule(){
        const addItemCodeLinks = this.addItemCodeLinks;
        const getTextNodes = this.getTextNodes;
        const unhideTruncatedText = this.unhideTruncatedText
        var includes = $('[data-include]');
        // const staticpath = "/static/static/prodverse/html/Kinpak%2C%20Inc/Production%20-%20Web%20Parts/";
        const staticpath = "/dynamic/html/"

         // Function to append a random string to the HTML file name
        function appendCacheBusting(file) {
            const uniqueid = new Date().getTime();
            const parts = file;
            return parts + '?v=' + uniqueid;
        }

        function determineProdLine(scheduleFileName) {
            let prodLine;
            if (scheduleFileName.includes("horix")) {
                prodLine = 'Hx';
            } else if (scheduleFileName.includes("inline")) {
                prodLine = 'INLINE';
            } else if (scheduleFileName.includes("blister")) {
                prodLine = 'BLISTER';
            } else if (scheduleFileName.includes("pdschedule")) {
                prodLine = 'PD LINE';
            } else if (scheduleFileName.includes("jbschedule")) {
                prodLine = 'JB LINE';
            } else if (scheduleFileName.includes("oil")) {
                prodLine = 'OIL LINE';
            } else if (scheduleFileName.includes("kit")) {
                prodLine = 'KITS LINE';
            } else if (scheduleFileName.includes("pouch")) {
                prodLine = 'POUCH';
            }
            return prodLine;
        }
        

        function loadSchedule(fileName) {
            console.log(`loadSchedule was passed the arg ${fileName}`);
            let prodLine = determineProdLine(fileName);
            // Load Inline schedule as default
            let filePath = staticpath + fileName
            let fileBusted = appendCacheBusting(filePath)
            $(includes).load(fileBusted, function() {
                // Get all the text nodes in the page
                const textNodes = getTextNodes();
                // Iterate through the text nodes and remove non-ASCII characters
                textNodes.forEach(node => {
                    node.nodeValue = node.nodeValue.replace(/[^\x00-\x7F]/g, "");
                });

                unhideTruncatedText();

                // Blister Schedule Customizations
                if (fileName === 'blisterschedule.html') {
                    // Hide blend, bottle, and cap columns
                    $('td:nth-child(10)').remove();
                    $('td:nth-child(9)').remove();
                    $('td:nth-child(6)').remove();
                };
            
                // Kit + Oil Schedule Remove Blend Column
                if (fileName ===  'kitschedule.html' || fileName === 'oilschedule.html') {
                    $('td:nth-child(6)').remove();
                };

                // Link to Specsheet
                addItemCodeLinks(prodLine);
            });
                // Put buttons in array
                const scheduleButtons = ['horixbutton', 'inlinebutton', 'blisterbutton', 'pdbutton', 'jbbutton', 'oilbutton', 'pouchbutton', 'kitbutton'];
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

                                unhideTruncatedText();
                                
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
                                prodLine = determineProdLine(file);                         
                                addItemCodeLinks(prodLine);
                            });
                        });
                    });
            });
        }
        

        let timeoutStored;

        function checkForUpdates(scheduleName) {
            console.log("checking for updates");
            $.ajax({
                url: `/prodverse/get_last_modified/${scheduleName}/`,
                dataType: "json",
                success: function (data) {
                    if (lastKnownModified === null) {
                        lastKnownModified = data.last_modified;
                        console.log("lmod" + lastKnownModified);
                    } else if (lastKnownModified !== data.last_modified) {
                        console.log("New file detected for " + scheduleName);
                        lastKnownModified = data.last_modified;
                        loadSchedule(scheduleName);
                    }
                },
                complete: function () {
                    clearTimeout(timeoutStored);
                    timeoutStored = setTimeout(() => checkForUpdates(scheduleName), 10000); // Check for updates every 10 seconds, adjust as needed
                },
            });
        }
        
        function stopCheckingForUpdates() {
            clearTimeout(timeoutStored);
        }
    
        const scheduleButtons = ["horixbutton", "inlinebutton", "blisterbutton", "pdbutton", "jbbutton", "oilbutton", "pouchbutton", "kitbutton"];
        scheduleButtons.forEach((buttonId) => {
            $.each(includes, function () {
                $(`#${buttonId}`).click(() => {
                    let scheduleName = `${buttonId.replace("button", "schedule")}.html`;
                    loadSchedule(scheduleName);
                    localStorage.setItem("lastViewedSchedule", scheduleName);
                    lastKnownModified = null;
                    stopCheckingForUpdates();
                    checkForUpdates(scheduleName);
                });
            });
        });
    
        let lastKnownModified = null;
        const lastViewedSchedule = localStorage.getItem("lastViewedSchedule");
        if (lastViewedSchedule) {
            loadSchedule(lastViewedSchedule);
            stopCheckingForUpdates();
            checkForUpdates(lastViewedSchedule);
        } else {
            loadSchedule("inlineschedule.html");
            stopCheckingForUpdates();
            checkForUpdates("inlineschedule.html");
        }
    }; 

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
                    const img = document.createElement('img');
                    img.id = 'Harvey';
                    img.src = '/static/static/core/media/kevin-gates-rbs-intro.gif'; // Adjust the path as necessary
                    img.style.position = 'fixed';
                    img.style.top = '0';
                    img.style.left = '0';
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.zIndex = '1000';
                    img.style.opacity = '50%';
                    document.body.appendChild(img);
                    
                    const offlineText = document.createElement('div');
                    offlineText.id = 'offlineText'
                    offlineText.textContent = 'You offline, sucka!';
                    offlineText.style.position = 'fixed';
                    offlineText.style.top = '50%';
                    offlineText.style.left = '50%';
                    offlineText.style.transform = 'translate(-50%, -50%)';
                    offlineText.style.color = 'white';
                    offlineText.style.fontSize = '8em';
                    offlineText.style.zIndex = '1001';
                    offlineText.style.animation = 'flashRainbow 1s infinite, wiggle 0.5s infinite';
                    offlineText.style.width = '100%';
                    offlineText.style.textAlign = 'center';
                    offlineText.style.fontFamily = 'Impact, Charcoal, sans-serif';
                    offlineText.style.textShadow = '2px 2px 5px #000000';
                    document.body.appendChild(offlineText);

                    const style = document.createElement('style');
                    style.textContent = `
                        @keyframes flashRainbow {
                            0% { color: red; }
                            14% { color: orange; }
                            28% { color: yellow; }
                            42% { color: green; }
                            57% { color: blue; }
                            71% { color: indigo; }
                            85% { color: violet; }
                            100% { color: red; }
                        }
                        @keyframes wiggle {
                            0%, 100% { transform: translate(-50%, -50%) rotate(0deg); }
                            25% { transform: translate(-50%, -50%) rotate(5deg); }
                            50% { transform: translate(-50%, -50%) rotate(-5deg); }
                            75% { transform: translate(-50%, -50%) rotate(5deg); }
                        }
                    `;
                    document.head.appendChild(style);
                    
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

};

export class SpecSheetPage {
    constructor() {
        try {
            this.state_json = JSON.parse($("#state_json").text().replaceAll("'",'"'));
        } catch(err) {
            console.error(err.message);
        };
        try {
            this.setupSpecSheetPage();
            this.drawSignature = this.drawSignature.bind(this);
            this.savePdf = this.savePdf.bind(this);
            console.log("Instance of class SpecSheetPage created.");
            this.initializeFromStateJson();
            $("#savePdf").on("click", this.savePdf);
            $("#signature1").drawSignature(this.val(), document.getElementById("canvas1"));
            $("#signature2").drawSignature(this.val(), document.getElementById("canvas2"));
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

    savePdf() {
        window.jsPDF = window.jspdf.jsPDF;
        $('#savePdf').addClass("hidden");
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