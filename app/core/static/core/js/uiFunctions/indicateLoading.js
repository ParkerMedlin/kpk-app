export function indicateLoading(whichField) {
    if (whichField=="itemCode") {
        $itemDescriptionInput.val("");
    } else {
        $itemCodeInput.val("");
    }
    $itemLocation.text("");
    $itemQty.text("");
    $animation.toggle();
    $itemCodeInput.addClass('loading');
    $itemDescriptionInput.addClass('loading');
}