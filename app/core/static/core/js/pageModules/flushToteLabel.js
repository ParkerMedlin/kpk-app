import { FlushToteLabelPage } from '../objects/pageObjects.js';
import { ZebraPrintButton } from '../objects/buttonObjects.js';

$(document).ready(function(){
    const thisFlushToteLabelPage = new FlushToteLabelPage();
    const thisZebraPrintButton = new ZebraPrintButton(document.getElementById("blendLabelPrintButton"), false);
    // id_flush_tote_type
});