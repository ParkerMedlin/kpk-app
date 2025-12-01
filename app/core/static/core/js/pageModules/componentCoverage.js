import { ComponentCoveragePage } from '../objects/pageObjects.js'

$(document).ready(function() {
    const coveragePage = new ComponentCoveragePage(window.componentCoverageData || {});

    $('#refreshCoverageBtn').on('click', function() {
        const $btn = $(this);
        $btn.prop('disabled', true).text('Refreshing...');

        fetch('/core/component-stock-coverage/data/')
            .then(response => response.json())
            .then(data => {
                coveragePage.updateData(data);
            })
            .catch(err => {
                console.error('Failed to refresh component coverage data', err);
                alert('Could not refresh right now. Please try again in a moment.');
            })
            .finally(() => {
                $btn.prop('disabled', false).text('Refresh Snapshot');
            });
    });
});
