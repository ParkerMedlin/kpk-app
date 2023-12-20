export async function sendImageToServer(formData) {
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