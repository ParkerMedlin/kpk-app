export class CreateCountListButton {
    constructor() {
        this.setUpCountListButton();
    };
    setUpCountListButton() {
        $('#create_list').click(function() {
            let itemCodes = [];
            $('td input:checked').each(function() {
                itemCodes.push($(this).attr("name"));
            });
            // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
            let encodedItemCodes = btoa(JSON.stringify(itemCodes));
            let dummyList = ["No_Item_Codes"];
            let encodedDummyList = btoa(JSON.stringify(dummyList));
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            let baseURL = window.location.href.split('core')[0];
            window.location.replace(baseURL + "core/countlist/add/"+encodedItemCodes+'/'+encodedDummyList)
        });
    };
};