$(document).ready(function(){
    const $emailSubmissionsLink = $("#emailSubmissionsLink");
    const $emailIssuesLink = $("#emailIssuesLink");
    const checkboxInputs = document.querySelectorAll('.recipientCheckBox');

    checkboxInputs.forEach(function(checkBox) {
        checkBox.addEventListener('click', function(){
            let emailRecipients = '';
            let emailSubmissionHref = '/core/email-submission-report?recipient=';
            let emailIssuesHref = '/core/email-issue-report?recipient=';
            checkboxInputs.forEach(function(checkBox) {
                if (checkBox.checked){
                    emailRecipients += checkBox.value + '%2C';
                };
            });
            
            emailSubmissionHref += emailRecipients;
            $emailSubmissionsLink.prop('href', emailSubmissionHref);
            emailIssuesHref += emailRecipients;
            $emailIssuesLink.prop('href', emailIssuesHref);
        });
    });
});
