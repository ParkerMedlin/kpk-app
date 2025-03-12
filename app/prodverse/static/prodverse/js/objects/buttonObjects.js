import { getBlendLabelFields, getMostRecentLotRecords } from '../requestFunctions/requestFunctions.js';

export class ZebraPrintButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            let labelContainer = document.querySelector("#labelContainer")
            let scale = 300 / 96; // Convert from 96 DPI (default) to 300 DPI
            let canvasOptions = {
                scale: scale
            };
            let labelLimit = $("#labelQuantity").val();
            let button = e.currentTarget;
            if (labelLimit > 30) {
                window.alert("Too many labels. Can only print 30 or fewer at a time.")
            } else {
                labelContainer.style.transform = "rotate(90deg)";
                labelContainer.style.border = "";
                html2canvas(labelContainer, canvasOptions).then(canvas => {
                    let labelQuantity = $("#labelQuantity").val();
                    canvas.toBlob(function(labelBlob) {
                        let formData = new FormData();
                        formData.append('labelBlob', labelBlob, 'label.png'); // 'filename.png' is the filename
                        formData.append('labelQuantity', labelQuantity);
                        sendImageToServer(formData);
                        }, 'image/jpeg');
                });
                labelContainer.style.transform = "";
                labelContainer.style.border = "1px solid black";
                let blendLabelDialog = document.querySelector("#blendLabelDialog");
                blendLabelDialog.close();
            }
            
        });
    };
}

export class MassZebraPrintButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpEventListener(button, recordType) {
        button.addEventListener('click', function(e) {
            const countRecordID = button.getAttribute('data-countrecord-id');
            const blendItemCode = button.getAttribute('data-itemCode');
            const blendItemDescription = button.getAttribute('data-itemDescription');
            


            // Create a list of values from container inputs
            const containerInputs = document.querySelectorAll(`tr.containerRow[data-countrecord-id="${countRecordID}"] input[data-countrecord-id="${countRecordID}"]`);
            const containerValues = Array.from(containerInputs).map(input => input.value);

            console.log("Container values:", containerValues);

            const containerCount = document.querySelectorAll(`tr.containerRow[data-countrecord-id="${countRecordID}"]`).length;


            // console.log(`Number of containers for count record ${countRecordID}: ${containerCount}`);

            // You can use this containerCount variable for further processing if needed
            let labelContainer = document.querySelector("#labelContainer");
            let scale = 300 / 96; // Convert from 96 DPI (default) to 300 DPI
            let canvasOptions = {
                scale: scale
            };

            let button = e.currentTarget;
            
            labelContainer.style.transform = "rotate(90deg)";
            labelContainer.style.border = "";
            html2canvas(labelContainer, canvasOptions).then(canvas => {
                let labelQuantity = $("#labelQuantity").val();
                canvas.toBlob(function(labelBlob) {
                    let formData = new FormData();
                    formData.append('labelBlob', labelBlob, 'label.png'); 
                    formData.append('labelQuantity', labelQuantity);
                    sendImageToServer(formData);
                    }, 'image/jpeg');
            });
            labelContainer.style.transform = "";
            labelContainer.style.border = "1px solid black";
            let blendLabelDialog = document.querySelector("#blendLabelDialog");
            blendLabelDialog.close();
            
            
        });
    };
}

export class CreateBlendLabelButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    };
    
    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            populateLotNumberDropdown(e.currentTarget.getAttribute("data-encoded-item-code"))
            let blendInformation = getBlendLabelFields(e.currentTarget.getAttribute("data-encoded-item-code"), e.currentTarget.getAttribute("data-lot-number"));
            $("#blend-label-item-code").text(blendInformation.item_code);
            $("#blend-label-item-description").text(blendInformation.item_description);
            $("#blend-label-lot-number").text(blendInformation.lotNumber);
            let itemProtection;
            $("#blend-label-uv-img").hide();
            $("#blend-label-freeze-img").hide();
            $("#blend-label-blank-freeze-img").hide();
            $("#blend-label-blank-uv-img").hide();
            if (blendInformation.uv_protection == 'yes' && blendInformation.freeze_protection == 'yes'){
                itemProtection = "UV and Freeze Protection Required";
                let uvImg = $('#blend-label-uv-img');
                uvImg.appendTo('#uvProtectionContainer');
                uvImg.show();
                let freezeImg = $('#blend-label-freeze-img');
                freezeImg.appendTo('#freezeProtectionContainer');
                freezeImg.show();
            } else if (blendInformation.uv_protection == 'no' && blendInformation.freeze_protection == 'yes'){
                itemProtection = "Freeze Protection Required";
                let freezeImg = $('#blend-label-freeze-img');
                freezeImg.appendTo('#freezeProtectionContainer');
                freezeImg.show();
                let blankUVImg = $('#blend-label-blank-uv-img');
                blankUVImg.appendTo('#uvProtectionContainer');
                blankUVImg.show();
            } else if (blendInformation.uv_protection == 'yes' && blendInformation.freeze_protection == 'no'){
                itemProtection = "UV Protection Required";
                let uvImg = $('#blend-label-uv-img');
                uvImg.appendTo('#uvProtectionContainer');
                uvImg.show();
                let blankFreezeImg = $('#blend-label-blank-freeze-img');
                blankFreezeImg.appendTo('#freezeProtectionContainer');
                blankFreezeImg.show();
            } else {
                itemProtection = "No Protection Required";
                let blankUVImg = $('#blend-label-blank-uv-img');
                blankUVImg.appendTo('#uvProtectionContainer');
                blankUVImg.show();
                let blankFreezeImg = $('#blend-label-blank-freeze-img');
                blankFreezeImg.appendTo('#freezeProtectionContainer');
                blankFreezeImg.show();
            };
            $("#blend-label-protection").text(itemProtection);



            function populateLotNumberDropdown(encodedItemCode) {
                let dropdown = $("#label-lot-number-dropdown");
                dropdown.empty(); // Clear existing options
                let lotNumbers = getMostRecentLotRecords(encodedItemCode);
                document.getElementById("label-lot-number-dropdown").addEventListener("click", function(e) {
                    let optionValue = e.currentTarget.value;
                    $("#blend-label-lot-number").text(optionValue);
                })
        
                for (let key in lotNumbers) {
                    let option = document.createElement("option");
                    option.text = `${key} (${lotNumbers[key]} gal on hand)`;
                    option.value = key;
                    dropdown.append(option);
        
                    option.addEventListener('click', function(e) {
                        let optionValue = e.currentTarget.value;
                        $("#blend-label-lot-number").text(optionValue);
                    })
                }
            }
        });
    }
}