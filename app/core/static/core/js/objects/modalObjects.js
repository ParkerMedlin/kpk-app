import { getAllBOMFields, getItemInfo, getURLParameter, getContainersFromCount } from '../requestFunctions/requestFunctions.js';
import { indicateLoading } from '../uiFunctions/uiFunctions.js';

export class DeleteFoamFactorModal {
    modalButtonLink = document.getElementById("deleteFoamFactorModalButtonLink");
    modalLabel = document.getElementById("deleteFoamFactorModalLabel");
    modalBody = document.getElementById("deleteFoamFactorModalBody");
    modalButton = document.getElementById("deleteFoamFactorModalButton");
    modalButtonLink = document.getElementById("deleteFoamFactorModalButtonLink")

    setModalButtons(e) {
        try {
            let lot_id = e.currentTarget.getAttribute("dataitemid");
            document.getElementById("deleteFoamFactorModalButtonLink").setAttribute("href", `/core/delete-foam-factor/${lot_id}`);
            console.log("DeleteFoamFactorModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
};

export class DeleteLotNumModal {
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink");
    modalLabel = document.getElementById("deleteLotNumModalLabel");
    modalBody = document.getElementById("deleteLotNumModalBody");
    modalButton = document.getElementById("deleteLotNumModalButton");
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink")

    setModalButtons(e) {
        try {
            let lot_ids = e.currentTarget.getAttribute("dataitemid");
            let lot_id_arr = lot_ids.split(',');
            console.log(lot_id_arr.length);
            console.log(lot_id_arr);
            if (lot_id_arr.length > 1) {
                document.getElementById("deleteLotNumModalQuestion").innerHTML = "Are you sure you want to delete these records?"
            }
            let encoded_list = btoa(JSON.stringify(lot_ids));
            document.querySelectorAll('.rowCheckBox').forEach(checkBox => {
                checkBox.checked = false;
            });
            document.getElementById("deleteLotNumModalButtonLink").setAttribute("href", `/core/delete-lot-num-records/${encoded_list}`);
            console.log("DeleteLotNumModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
};

export class EditConfirmCountRecordModal {
    modalButtonLink = $("#editCountRecordsModalButtonLink");
    modalLabel = document.getElementById("editCountRecordsModalLabel");
    modalBody = document.getElementById("editCountRecordsModalBody");
    modalButton = document.getElementById("editCountRecordsModalButton");
    modalButtonLink = document.getElementById("editCountRecordsModalButtonLink");

    setModalButtons(e) {
        try {
            let count_id = e.currentTarget.getAttribute("dataitemid");
            let encoded_list = btoa(JSON.stringify(count_id));
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
            $("#editCountRecordsModalButtonLink").attr("href", `/core/count-list/display/${encoded_list}?recordType=${recordType}`);
            console.log("EditConfirmCountRecordModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
}

export class EditLotNumModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            this.setLotNumberFieldReadOnly();
            console.log("Instance of class EditLotNumModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = document.getElementById("id_editLotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_editLotNumModal-item_description");
    quantityInput = document.getElementById("id_editLotNumModal-lot_quantity");
    lineInput = document.getElementById("id_editLotNumModal-line");
    deskInput = document.getElementById("id_editLotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_editLotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    formElement = $("#addLotNumFormElement");
    BOMFields = getAllBOMFields('blend');

    setLotNumberFieldReadOnly() {
        document.getElementById("id_editLotNumModal-lot_number").setAttribute("readonly", true);
    }

    setAddLotModalInputs(e) {
        $('#id_editLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_editLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        if (e.currentTarget.getAttribute('data-lotqty')){
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        } else if (e.currentTarget.getAttribute('data-totalqty')) {
            let thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty'))));
        }
        $('#id_editLotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_editLotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        $("#id_editLotNumModal-run_date").val(e.currentTarget.getAttribute('data-rundate'));
    };

    setFields(itemData) {
        $('#id_editLotNumModal-item_code').val(itemData.item_code);
        $('#id_editLotNumModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_editLotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $('#id_editLotNumModal-item_code').val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $("#id_editLotNumModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_editLotNumModal-item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_editLotNumModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_editLotNumModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    setUpEventListeners() {
        $('#id_editLotNumModal-line').change(function(){
            if ($('#id_editLotNumModal-line').val() == 'Prod') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            } else if ($('#id_editLotNumModal-line').val() == 'Hx') {
                $('#id_editLotNumModal-desk').val('Horix');
            } else if ($('#id_editLotNumModal-line').val() == 'Dm') {
                $('#id_editLotNumModal-desk').val('Drums');
            } else if ($('#id_editLotNumModal-line').val() == 'Totes') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            } else if ($('#id_editLotNumModal-line').val() == 'Pails') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            };
        });
    };

};

export class EditFoamFactorModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            console.log("Instance of class EditFoamFactorModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = document.getElementById("id_editFoamFactorModal-item_code");
    itemDescriptionInput = document.getElementById("id_editFoamFactorModal-item_description");
    $addFoamFactorButton = $("#addFoamFactorButton");
    formElement = $("#addFoamFactorFormElement");
    BOMFields = getAllBOMFields('foam-factor-blends');


    setAddFoamFactorModalInputs(e) {
        $('#id_editFoamFactorModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_editFoamFactorModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
    };

    setFields(itemData) {
        $('#id_editFoamFactorModal-item_code').val(itemData.item_code);
        $('#id_editFoamFactorModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_editFoamFactorModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $('#id_editFoamFactorModal-item_code').val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $("#id_editFoamFactorModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_editFoamFactorModal-item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_editFoamFactorModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_editFoamFactorModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    setUpEventListeners() {
        $('#id_editFoamFactorModal-line').change(function(){
            if ($('#id_editFoamFactorModal-line').val() == 'Prod') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Hx') {
                $('#id_editFoamFactorModal-desk').val('Horix');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Dm') {
                $('#id_editFoamFactorModal-desk').val('Drums');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Totes') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Pails') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            };
        });
    };

};

export class AddFoamFactorModal {
    constructor(){
        try {
            this.setUpAutofill();
        console.log("Instance of class AddFoamFactorModal created.");
        } catch(err) {
            console.error(err.message);
        };
    }

    itemCodeInput = document.getElementById("id_addFoamFactorModal-item_code");
    itemDescriptionInput = document.getElementById("id_addFoamFactorModal-item_description");
    addFoamFactorButton = document.getElementById("addFoamFactorButton");
    $addFoamFactorButton = $("#addFoamFactorButton");
    formElement = $("#addFoamFactorFormElement");
    BOMFields = getAllBOMFields('foam-factor-blends');


    setAddLotModalInputs(e) {
        $('#id_addFoamFactorModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_addFoamFactorModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
    };

    setFields(itemData) {
        $('#id_addFoamFactorModal-item_code').val(itemData.item_code);
        $('#id_addFoamFactorModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_addFoamFactorModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $('#id_addFoamFactorModal-item_code').val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $("#id_addFoamFactorModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_addFoamFactorModal-item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_addFoamFactorModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_addFoamFactorModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

};

export class AddLotNumModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            this.setLotNumberFieldReadOnly();
            this.canvas = this.createCanvas();
            this.ctx = this.canvas.getContext('2d');
            this.particles = [];
            this.animationId = null;
        console.log("Instance of class AddLotNumModal created.");
        } catch(err) {
            console.error(err.message);
        };
    }

    itemCodeInput = document.getElementById("id_addLotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_addLotNumModal-item_description");
    quantityInput = document.getElementById("id_addLotNumModal-lot_quantity");
    lineInput = document.getElementById("id_addLotNumModal-line");
    deskInput = document.getElementById("id_addLotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_addLotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    formElement = $("#addLotNumFormElement");
    BOMFields = getAllBOMFields('blend');

    setLotNumberFieldReadOnly() {
        $("#id_addLotNumModal-lot_number").prop('readonly', true);
    }

    setAddLotModalInputs(e) {
        $('#id_addLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_addLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        let thisQuantity;
        if (e.currentTarget.getAttribute('data-lotqty')){
            thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty')));
        } else if (e.currentTarget.getAttribute('data-totalqty')) {
            thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty')));
        }
        if (e.currentTarget.getAttribute('data-line') == 'Prod' && thisQuantity > 2800) {
            thisQuantity = 2800;
        }
        $('#id_addLotNumModal-lot_quantity').val(thisQuantity);
        $('#id_addLotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_addLotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        console.log(e.currentTarget.getAttribute('data-rundate'));
        // Convert date format from mm/dd/yyyy to yyyy-MM-dd
        if (e.currentTarget.getAttribute('data-rundate')) {
            let originalDate = e.currentTarget.getAttribute('data-rundate');
            // Check if the originalDate contains a '/' character
            if (originalDate.includes('/')) {
                let dateParts = originalDate.split('/');
                if (dateParts.length === 3) {
                    let year = dateParts[2];
                    let month = dateParts[0].padStart(2, '0');
                    let day = dateParts[1].padStart(2, '0');
                    let formattedDate = `${year}-${month}-${day}`;
                    $('#id_addLotNumModal-run_date').val(formattedDate);
                } else {
                    console.error('Invalid date format');
                    $('#id_addLotNumModal-run_date').val('');
                }
            } else {
                $('#id_addLotNumModal-run_date').val(e.currentTarget.getAttribute('data-rundate'));
            }
        } else {
            $('#id_addLotNumModal-run_date').val('');
        }
    };

    setFields(itemData) {
        $('#id_addLotNumModal-item_code').val(itemData.item_code);
        $('#id_addLotNumModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_addLotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $('#id_addLotNumModal-item_code').val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $("#id_addLotNumModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_addLotNumModal-item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_addLotNumModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_addLotNumModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    createCanvas() {
        const canvas = document.createElement('canvas');
        Object.assign(canvas.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: '9999'
        });
        document.body.appendChild(canvas);
        this.resizeCanvas(canvas);
        window.addEventListener('resize', () => this.resizeCanvas(canvas));
        return canvas;
    }

    resizeCanvas(canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    createParticle(x, y, exploding = false) {
        const hue = Math.random() * 360;
        const angle = Math.random() * Math.PI;
        const speed = exploding ? Math.random() * 15 + 5 : Math.random() * 3 + 2;
        return {
            x: x || Math.random() * this.canvas.width,
            y: y || 0,
            size: Math.random() * 6 + 6,
            color: `hsl(${hue}, 100%, 50%)`,
            speedY: Math.sin(angle) * speed,
            speedX: Math.cos(angle) * speed,
            spin: Math.random() * 0.2 - 0.1,
            rotateSpeed: Math.random() * 0.01 - 0.005,
            gravity: 0.1,
            bounce: 0.8,
            alpha: 1,
            decay: Math.random() * 0.02 + 0.02
        };
    }

    updateParticles() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.particles.forEach((p, index) => {
            p.speedY += p.gravity;
            p.y += p.speedY;
            p.x += p.speedX;
            p.spin += p.rotateSpeed;
            p.alpha -= p.decay;

            if (p.x < 0 || p.x > this.canvas.width) {
                p.speedX *= -p.bounce;
                p.x = p.x < 0 ? 0 : this.canvas.width;
            }
            if (p.y > this.canvas.height) {
                p.speedY *= -p.bounce;
                p.y = this.canvas.height;
                p.speedX *= 0.9;
            }

            p.speedX *= 0.99;
            p.speedY *= 0.99;

            this.ctx.save();
            this.ctx.translate(p.x, p.y);
            this.ctx.rotate(p.spin);
            this.ctx.globalAlpha = p.alpha;
            this.ctx.fillStyle = p.color;
            this.ctx.shadowColor = p.color;
            this.ctx.shadowBlur = 10;
            this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
            this.ctx.restore();

            if (p.alpha <= 0) {
                this.particles.splice(index, 1);
            }
        });

        if (this.particles.length > 0) {
            this.animationId = requestAnimationFrame(() => this.updateParticles());
        } else {
            this.stopConfetti();
        }
    }

    launchConfettiBurst() {
        const originX = this.canvas.width / 2;
        const originY = 0;
        const newParticles = Array.from({ length: 20 }, () => this.createParticle(originX, originY, true));
        this.particles.push(...newParticles);
    }

    startConfettiSequence() {
        let burstCount = 0;
        const totalBursts = 100;
        const burstInterval = 5; // milliseconds

        const triggerBurst = () => {
            if (burstCount < totalBursts) {
                this.launchConfettiBurst();
                burstCount++;
                setTimeout(triggerBurst, burstInterval);
            }
        };

        this.updateParticles();
        triggerBurst();
    }

    stopConfetti() {
        cancelAnimationFrame(this.animationId);
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    setUpEventListeners() {
        $('#id_addLotNumModal-line').change(function(){
            if ($('#id_addLotNumModal-line').val() == 'Prod') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Hx') {
                $('#id_addLotNumModal-desk').val('Horix');
            } else if ($('#id_addLotNumModal-line').val() == 'Dm') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Totes') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Pails') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            };
        });
        
        // document.querySelector('#addNewLotNumRecord').addEventListener('click', (e) => {
        //     e.preventDefault(); // Prevent form submission
        //     this.startConfettiSequence();
            
        //     // Submit the form after a delay to allow confetti to start
        //     setTimeout(() => {
        //         document.querySelector('#addLotNumFormElement').submit();
        //     }, 100);
        // });
        
        // $('#addLotNumModal').click(function(){
        $('#addLotNumModal').on('shown.bs.modal', function () {
            let latestLotNumber;
            $.ajax({
                url: '/core/get-latest-lot-num-record/',
                async: false,
                dataType: 'json',
                success: function(data) {
                    latestLotNumber = data;
                }
            });

            const today = new Date();
            const monthLetterAndYear = String.fromCharCode(64 + today.getMonth() + 1) + String(today.getFullYear()).slice(-2);
            const fourDigitNumber = String(parseInt(latestLotNumber.lot_number.toString().slice(-4)) + 1).padStart(4, '0');
            const nextLotNumber = monthLetterAndYear + fourDigitNumber;

            $("#id_addLotNumModal-lot_number").val(nextLotNumber);

        });

        $('#addLotNumDuplicateSelector').on('change', function () {
            const duplicateCount = $(this).val()
            console.log(duplicateCount)
            $('#addLotNumFormElement').prop('action', `/core/add-lot-num-record/?redirect-page=lot-num-records&duplicates=${duplicateCount}&redirect-page=blend-schedule`)
        });
       
    };

};

export class AddCountListItemModal {
    constructor(thisCountListWebSocket){
        try {
            this.setUpAutofill(thisCountListWebSocket);
            console.log("Instance of class AddCountListItemModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = $("#id_countListModal_item_code");
    itemDescriptionInput = $("#id_countListModal_item_description");
    BOMFields = getAllBOMFields(getURLParameter('recordType'));

    setModalButtonLink(itemCode, thisCountListWebSocket) {
        $('#addCountButton').off();
        $('#addCountButton').click(function(){
            console.log("click the fucking button");
            let recordType = getURLParameter('recordType');
            let listId = getURLParameter('listId');
            thisCountListWebSocket.addCount(recordType, listId, itemCode);
        })
    }

    setFields(itemData) {
        $('#id_countListModal_item_code').val(itemData.item_code);
        $('#id_countListModal_item_description').val(itemData.item_description);
    };

    setUpAutofill(thisCountListWebSocket) {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setModalButtonLink = this.setModalButtonLink;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_countListModal_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_countListModal_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setModalButtonLink(itemCode, thisCountListWebSocket);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setModalButtonLink(itemCode, thisCountListWebSocket);
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_countListModal_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_countListModal_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setModalButtonLink(itemCode, thisCountListWebSocket);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setModalButtonLink(itemCode, thisCountListWebSocket);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_countListModal_item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_countListModal-item_description").focus(function(){
            $('.animation').hide();
        });
    }
    

}

export function calculateVarianceAndCount(countRecordId){
    const quantityInputs = $(`input.form-control.container_quantity[data-countrecord-id="${countRecordId}"]`);
    let totalQuantity = 0;
    quantityInputs.each(function() {
        const value = parseFloat($(this).val()) || 0;
        totalQuantity += value;
    });
    $(`input.counted_quantity[data-countrecord-id="${countRecordId}"]`).val(totalQuantity);
    const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text());
    const variance = totalQuantity - expectedQuantity;
    $(`td.tbl-cell-variance[data-countrecord-id="${countRecordId}"]`).text(variance.toFixed(2));
};

export function sendCountRecordChange(eventTarget, thisCountListWebSocket, containerId) {
    function updateDate(eventTarget){
        let correspondingID = eventTarget.attr('correspondingrecordid');
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        $(`td[data-countrecord-id="${correspondingID}"]`).find("input[name*='counted_date']").val(formattedDate);
    };

    function calculateVarianceAndCount(countRecordId){
        const quantityInputs = $(`input.form-control.container_quantity[data-countrecord-id="${countRecordId}"]`);
        let totalQuantity = 0;
        quantityInputs.each(function() {
            const value = parseFloat($(this).val()) || 0;
            totalQuantity += value;
        });
        $(`input.counted_quantity[data-countrecord-id="${countRecordId}"]`).val(totalQuantity);
        const expectedQuantity = parseFloat($(`span.expected-quantity-span[data-countrecord-id="${countRecordId}"]`).text());
        const variance = totalQuantity - expectedQuantity;
        $(`td.tbl-cell-variance[data-countrecord-id="${countRecordId}"]`).text(variance.toFixed(2));
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
    // containers.forEach(container => {
    //     console.log(`Container ID: ${container.container_id}`);
    //     console.log(`Container Quantity: ${container.container_quantity}`);
    //     console.log(`Container Type: ${container.container_type}`);
    //     console.log(`Tare Weight: ${container.tare_weight}`);
    // });
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

// export class CountContainerModal {
//     constructor(thisCountListWebSocket){
//         try {
//             this.initializeContainerFields();
//             this.setUpEventListeners(thisCountListWebSocket);
//             this.setUpMutationObservers(thisCountListWebSocket);
//             console.log("Instance of class CountContainerModal created.");
//         } catch(err) {
//             console.error(err.message);
//         };
//     };

//     initializeContainerFields() {
//         // console.log('starting initializeContainerFields')
//         const recordType = getURLParameter('recordType');
//         // console.log(recordType);
//         $('#countsTable tbody tr.countRow').each(function() {
//             let containerTableBody = $(this).find('table.container-table');
//             // console.log(containerCell[0].outerHTML);
//             let countRecordId = $(this).attr('data-countrecord-id');
//             // console.log(`Starting on the count row for countRecordId: ${countRecordId}`);
//             // console.log(`table body:\n${containerTableBody.html()}`);
            
//             // Here you can add any additional logic to handle the countRecordId
//             let theseContainers = getContainersFromCount(countRecordId, recordType);
//             let tableRows = '';
//             if (theseContainers.length === 0) {
//                 console.log(`No containers found. Putting in a single blank container for ${countRecordId}`);
//                 tableRows += `
//                     <tr data-container-id="0" data-countrecord-id="${countRecordId}" class="containerRow">
//                         <td class='container_id' style="display:none;">
//                             <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="0" data-container-id="0">
//                         </td>
//                         <td class='quantity'><input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="" data-container-id="0"></td>
//                         <td class='container_type'>
//                             <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="0">
//                                 <option value="275gal tote" data-countrecord-id="${countRecordId}">275gal tote</option>
//                                 <option value="storage tank" data-countrecord-id="${countRecordId}">Storage Tank</option>
//                                 <option value="stainless steel tote" data-countrecord-id="${countRecordId}">Stainless Steel tote</option>
//                                 <option value="300gal tote" data-countrecord-id="${countRecordId}">300gal tote</option>
//                                 <option value="poly drum" data-countrecord-id="${countRecordId}">Poly Drum</option>
//                                 <option value="metal drum" data-countrecord-id="${countRecordId}">Metal Drum</option>
//                                 <option value="pail" data-countrecord-id="${countRecordId}">Pail</option>
//                                 <option value="gallon jug" data-countrecord-id="${countRecordId}">Gallon Jug</option>
//                             </select>
//                         </td>
//                         <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
//                             <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="" data-container-id="0">
//                         </td>
//                         <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="0"></i></td>
//                     </tr>
//                 `;
//             } else {
//                 theseContainers.forEach(container => {
//                     // console.log(`this is container ${container.container_id} for count record ${countRecordId}`);
//                     tableRows += `
//                         <tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
//                             <td class='container_id' style="display:none;">
//                                 <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="${container.container_id}" data-container-id="${container.container_id}">
//                             </td>
//                             <td class='quantity'>
//                                 <input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="${container.container_quantity || ''}" data-container-id="${container.container_id}">
//                             </td>
//                             <td class='container_type'>
//                                 <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
//                                     <option value="275gal tote" ${container.container_type === '275gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">275gal tote</option>
//                                     <option value="storage tank" ${container.container_type === 'storage tank' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Storage Tank</option>
//                                     <option value="stainless steel tote" ${container.container_type === 'stainless steel tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Stainless Steel tote</option>
//                                     <option value="300gal tote" ${container.container_type === '300gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">300gal tote</option>
//                                     <option value="poly drum" ${container.container_type === 'poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Poly Drum</option>
//                                     <option value="metal drum" ${container.container_type === 'metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Metal Drum</option>
//                                     <option value="pail" ${container.container_type === 'pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Pail</option>
//                                     <option value="gallon jug" ${container.container_type === 'gallon jug' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Gallon Jug</option>
//                                 </select>
//                             </td>
//                             <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
//                                 <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="${container.tare_weight || ''}" data-container-id="${container.container_id}">
//                             </td>
//                             <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i></td>
//                         </tr>
//                     `;
//                 });
//             };
//             containerTableBody.append(tableRows);
//         });
//     };

//     updateContainerFields(countRecordId, recordType, containerId){
//         let theseContainers = getContainersFromCount(countRecordId, recordType);
        
//         console.log(`logging the containers retreived from the database: ${theseContainers}`)
//         let tableRows = '';
//         let containerTableBody = $('#countsTable tbody tr[data-countrecord-id]').find('tbody.containerTbody')
//         // console.log(containerId)
//         // theseContainers.forEach(container => {
//         //     console.log(container);

//         // });

//         // console.log(containerTableBody.html());
//         if (theseContainers.length === 0) {
//             tableRows += `
//                 <tr data-container-id="0" data-countrecord-id="${countRecordId}" class="containerRow">
//                     <td class='container_id' style="display:none;">
//                         <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="0" data-container-id="0">
//                     </td>
//                     <td class='quantity'><input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="" data-container-id="0"></td>
//                     <td class='container_type'>
//                         <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="0">
//                             <option value="275gal tote" data-countrecord-id="${countRecordId}">275gal tote</option>
//                             <option value="storage tank" data-countrecord-id="${countRecordId}">Storage Tank</option>
//                             <option value="stainless steel tote" data-countrecord-id="${countRecordId}">Stainless Steel tote</option>
//                             <option value="300gal tote" data-countrecord-id="${countRecordId}">300gal tote</option>
//                             <option value="poly drum" data-countrecord-id="${countRecordId}">Poly Drum</option>
//                             <option value="metal drum" data-countrecord-id="${countRecordId}">Metal Drum</option>
//                             <option value="pail" data-countrecord-id="${countRecordId}">Pail</option>
//                             <option value="gallon jug" data-countrecord-id="${countRecordId}">Gallon Jug</option>
//                         </select>
//                     </td>
//                     <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
//                         <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="" data-container-id="0">
//                     </td>
//                     <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="0"></i></td>
//                 </tr>
//             `;
//         } else {
//             theseContainers.forEach(container => {
//                 tableRows += `
//                     <tr data-container-id="${container.container_id}" data-countrecord-id="${countRecordId}" class="containerRow">
//                         <td class='container_id' style="display:none;">
//                             <input type="number" class="form-control container_id" data-countrecord-id="${countRecordId}" value="${container.container_id}" data-container-id="${container.container_id}">
//                         </td>
//                         <td class='quantity'>
//                             <input type="number" class="form-control container_quantity" data-countrecord-id="${countRecordId}" value="${container.container_quantity || ''}" data-container-id="${container.container_id}">
//                         </td>
//                         <td class='container_type'>
//                             <select class="form-control container_type form-select" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}">
//                                 <option value="275gal tote" ${container.container_type === '275gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">275gal tote</option>
//                                 <option value="storage tank" ${container.container_type === 'storage tank' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Storage Tank</option>
//                                 <option value="stainless steel tote" ${container.container_type === 'stainless steel tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Stainless Steel tote</option>
//                                 <option value="300gal tote" ${container.container_type === '300gal tote' ? 'selected' : ''} data-countrecord-id="${countRecordId}">300gal tote</option>
//                                 <option value="poly drum" ${container.container_type === 'poly drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Poly Drum</option>
//                                 <option value="metal drum" ${container.container_type === 'metal drum' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Metal Drum</option>
//                                 <option value="pail" ${container.container_type === 'pail' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Pail</option>
//                                 <option value="gallon jug" ${container.container_type === 'gallon jug' ? 'selected' : ''} data-countrecord-id="${countRecordId}">Gallon Jug</option>
//                             </select>
//                         </td>
//                         <td class="tareWeight ${recordType === 'blend' ? 'hidden' : ''} tare_weight">
//                             <input type="number" class="form-control tare_weight" data-countrecord-id="${countRecordId}" value="${container.tare_weight || ''}" data-container-id="${container.container_id}">
//                         </td>
//                         <td><i class="fa fa-trash row-clear" data-countrecord-id="${countRecordId}" data-container-id="${container.container_id}"></i></td>
//                     </tr>
//                 `;
//             });
//         }
//         containerTableBody.children().remove();
//         containerTableBody.append(tableRows);
//         // containerCell.find('table tbody').html(tableRows);
//         const thisContainer = theseContainers[containerId];
//         const thisContainerRow = $(`tr[data-countrecord-id="${countRecordId}"][data-container-id="${containerId}"]`);
//         const quantityInput = thisContainerRow.find('input.container_quantity');
//         quantityInput.on('focus', function() {
//             let value = $(this).val();
//             // Use setTimeout to handle Chrome bug where cursor doesn't move to the end immediately
//             setTimeout(() => {
//                 // For 'number' input types, replace the value to move the cursor to the end
//                 if ($(this).attr('type') === 'number') {
//                     $(this).val(null).val(value); // Temporarily set to null and back to value to move cursor
//                 } else if ($(this).attr('type') === 'text') {
//                     let valueLength = value.length;
//                     this.setSelectionRange(valueLength, valueLength); // For text inputs, use setSelectionRange
//                 }
//             }, 0); // Delay of 0ms to ensure it runs after the focus event
//         });
//         quantityInput.focus();


//     }

//     setUpEventListeners(thisCountListWebSocket) {
//         $('select.container_type').off('change');
//         $('select.container_type').on('change', function() {
//             const containerId = $(this).attr('data-container-id');
//             console.log(`Passing containerId: ${containerId}`);
//             sendCountRecordChange($(this), thisCountListWebSocket, containerId);
//         });

//         $('.add-container-row').off('click');
//         $('.add-container-row').click(function() {
//             const recordId = this.getAttribute('data-countrecord-id');
//             const table = $(`table[data-countrecord-id="${recordId}"]`);
//             const rows = document.querySelectorAll(`table[data-countrecord-id="${recordId}"] tr`);
//             const lastRow = rows[rows.length - 1];
//             const newRow = lastRow.cloneNode(true);
//             $(newRow).find('input').val('');
//             const newRowContainerId = parseInt($(lastRow).attr('data-container-id')) + 1;
//             $(newRow).attr('data-container-id', newRowContainerId);
//             $(newRow).find('input.container_id').val(newRowContainerId);
//             $(newRow).find('input.container_quantity').attr('data-container-id', newRowContainerId);
//             $(newRow).find('.row-clear').click(function() {
//                 $(this).closest('tr').remove();
//             });
//             $(newRow).find('input.container_quantity').on('keyup', function() {
//                 calculateVarianceAndCount(recordId);
//                 sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
//             });
//             $(newRow).find('select.container_type').on('change', function() {
//                 sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
//             });
//             $(newRow).find('input.container_id').on('keyup', function() {
//                 calculateVarianceAndCount(recordId);
//                 sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
//             });
//             table.find('tbody tr:last').after(newRow);
//             sendCountRecordChange($(this), thisCountListWebSocket, newRowContainerId);
//         });

//         $('.row-clear').off('click');
//         $('.row-clear').click(function() {
//             $(this).closest('tr').remove();
//             const containerId = $(this).attr('data-container-id');
//             sendCountRecordChange($(this), thisCountListWebSocket, containerId);
//         });

//         $('.container_quantity').off('keyup');
//         $('.container_quantity').on('keyup', function() {
//             const containerId = $(this).attr('data-container-id');
//             // const countRecord = $(this).attr('data-countrecord-id');
//             // console.log(`sending an update for countrecord ${countRecord}, container ${containerId}`);
//             sendCountRecordChange($(this), thisCountListWebSocket, containerId);
//         });

//     };

//     setUpMutationObservers(thisCountListWebSocket) {
//         let setUpEventListeners = this.setUpEventListeners;
//         let updateContainerFields = this.updateContainerFields;

//         const containerMonitorObserver = new MutationObserver((mutationsList) => {
//             for (let mutation of mutationsList) {
//                 if (mutation.type === 'attributes' && mutation.attributeName === 'data-container-id-updated') {
//                     const countRecordId = mutation.target.getAttribute('data-countrecord-id');
//                     const updatedContainerId = mutation.target.getAttribute('data-container-id-updated');
//                     const recordType = getURLParameter('recordType');
//                     console.log(`Container monitor updated for countRecordId: ${countRecordId}, new containerId: ${updatedContainerId}`);
//                     updateContainerFields(countRecordId, recordType, updatedContainerId);
//                     setUpEventListeners(thisCountListWebSocket);
//                 }
//             }
//         });

//         // Observe changes to all div.container-monitor elements
//         document.querySelectorAll('div.container-monitor').forEach((element) => {
//             containerMonitorObserver.observe(element, { attributes: true });
//         });
//     };

// }