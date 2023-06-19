export class IssueSheetDropdown {
    constructor() {
        try {
            this.setUpIssueSheetLinks();
            console.log("Instance of class IssueSheetDropdown created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpIssueSheetLinks() {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const day = tomorrow.getDate();
        const month = tomorrow.getMonth()+1;
        const year = tomorrow.getFullYear();
        const tomorrowString = month+'-'+day+'-'+year;
        $("#inlineIssueSheetLink").prop("href", "/core/issue-sheets/INLINE/"+tomorrowString);
        $("#pdlineIssueSheetLink").prop("href", "/core/issue-sheets/PD LINE/"+tomorrowString);
        $("#jblineIssueSheetLink").prop("href", "/core/issue-sheets/JB LINE/"+tomorrowString);           
    };
}