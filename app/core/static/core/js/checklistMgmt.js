$(document).ready(function(){
    const $recipientSelect = $("#recipientSelect");
    const $emailSubmissionsLink = $("#emailSubmissionsLink");
    const $emailIssuesLink = $("#emailIssuesLink");

    $recipientSelect.change(function(){
        let emailSubmissionHref = '/core/emailsubmissionreport/';
        emailSubmissionHref+=$recipientSelect.val();
        $emailSubmissionsLink.prop('href', emailSubmissionHref);
        let emailIssuesHref = '/core/emailissuereport/';
        emailIssuesHref+=$recipientSelect.val();
        $emailIssuesLink.prop('href', emailIssuesHref);
    });
});
