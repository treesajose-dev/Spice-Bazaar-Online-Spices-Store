function resizeImage(input) {
    console.log("resizeImage function triggered");
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                console.log("Image loaded successfully");

                // Create a canvas with fixed 225x225 dimensions
                const canvas = document.createElement('canvas');
                const maxWidth = 225;  // Fixed width for the resized image
                const maxHeight = 225; // Fixed height for the resized image

                canvas.width = maxWidth;
                canvas.height = maxHeight;

                const ctx = canvas.getContext('2d');

                // Draw the image on the canvas
                // If the image doesn't match the 225x225 size, it will be scaled to fit
                ctx.drawImage(img, 0, 0, maxWidth, maxHeight);

                // Get the resized image as a base64 data URL
                const resizedDataUrl = canvas.toDataURL('image/jpeg');
                console.log("Resized image data URL: ", resizedDataUrl); // Debugging line

                // Save base64 string without the header (data:image/jpeg;base64,)
                document.getElementById('resized_image').value = resizedDataUrl.split(',')[1];
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}
