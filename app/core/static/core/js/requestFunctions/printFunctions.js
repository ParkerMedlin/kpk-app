export async function sendImageToServer(imageB64String, deviceJson, optionsJson) {
    // Convert the base64 string to a Blob
    let fetchResponse = await fetch(imageB64String);
    let blob = await fetchResponse.blob();
    formData.append('blob', blob, 'printImage.jpg');

    // Create a FormData object and append the Blob
    let formData = new FormData();
    formData.append('blob', blob, 'filename.jpg');

    // Send the FormData object to your Django server
    let response = await fetch('/core/print-blend-label/', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    } else {
        console.log('Image sent successfully');
    }
}