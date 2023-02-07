export function indicateLoading(whichField) {
    if (whichField=="itemCode") {
        $("#id_item_description").val("");
    } else {
        $("#id_item_code").val("");
    }
    $('#id_location').text("");
    $('#id_quantity').text("");
    $(".animation").toggle();
    $("#id_item_code").addClass('loading');
    $("#id_item_description").addClass('loading');
}