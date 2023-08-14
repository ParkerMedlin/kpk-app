export function updateCountCollection(thisPk,newCollectionId) {
    let results;
    $.ajax({
        url: `/core/update-count-collection-link?thisPk=${thisPk}&newCollectionId=${newCollectionId}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            results = data;
        }
    });
    return results;
}