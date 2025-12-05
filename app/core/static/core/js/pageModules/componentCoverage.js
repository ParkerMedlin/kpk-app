import { ComponentCoveragePage } from '../objects/pageObjects.js'

$(document).ready(function() {
    new ComponentCoveragePage(window.componentCoverageData || {});
});
