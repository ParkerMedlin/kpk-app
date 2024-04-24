$(document).ready(function() {
    const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
    ];


    const $emailLink = $("#emailLink");
    const countsTable = document.getElementById("countsTable");
    const todayDate = new Date();
    const monthNumber = todayDate.getMonth();
    const todayString = monthNames[monthNumber] + "%20" + String(todayDate.getDate()).padStart(2, '0') + "%20" + String(todayDate.getFullYear());
    let subjectString = `Counts%20for%20${todayString}`;
    
    $emailLink.attr('href', `mailto:jdavis@kinpakinc.com?cc=kkeyes@kinpakinc.com&subject=${subjectString}`);

    $emailLink.click(function(){
        var range = document.createRange();  
        range.selectNode(countsTable);
        window.getSelection().addRange(range);
        document.execCommand('copy');
    });

    var totalVarianceCell = $("#totalVarianceCell");
    var totalVarianceValue = Math.abs(parseFloat(totalVarianceCell.text().replace(/[^0-9.-]+/g,"")));
    if (totalVarianceValue > 1000) {
        totalVarianceCell.addClass('bigMoney');
    }
    
    
});