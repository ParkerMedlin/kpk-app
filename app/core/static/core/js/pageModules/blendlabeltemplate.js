import { ZebraPrintButton } from '../objects/buttonObjects.js';

$(document).ready(function(){
    const thisZebraPrintButton = new ZebraPrintButton(document.getElementById("blendLabelPrintButton"), true);
    $("#label-lot-number-dropdown").change(function(e) {
        let selectedOptionValue = this.value;
        $("#blend-label-lot-number").text(selectedOptionValue);
    });
});


