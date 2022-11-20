$(document).ready(function() {
    let $modalButtonLink = $("#modalButtonLink");
    const deleteButtons = document.querySelectorAll('.deleteBtn')
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', function setModalButton(e) {
            let count_id = 'ok';
            count_id = e.target.id;
            console.log(count_id);
            let encoded_list = btoa(JSON.stringify(count_id));
            $modalButtonLink.attr("href", `/core/delete_countrecord/countrecords/${encoded_list}/${encoded_list}`);
        });
    });

    let $createReportButton = $('#create-report');
    const checkBoxes = document.querySelectorAll('.reportCheckBox');
    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            $createReportButton.show();
        });
    });
});

$(document).ready(function() {
    $('#create-report').click(function() {
        let part_numbers = [];
        $('td input:checked').each(function() {
            part_numbers.push($(this).attr("name"));
        });
        console.log(part_numbers)
        if (part_numbers.length === 0) {
            alert("Please check at least one row to include in the report.")
        } else {
            // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
            let encoded_list = btoa(JSON.stringify(part_numbers));
            console.log(encoded_list)
            base_url = window.location.href.split('core')[0];
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            window.location.replace(base_url + "core/displayfinishedcounts/"+encoded_list)
        }
    });
});