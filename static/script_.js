// Handle file upload and progress bar
const uploadForm = document.getElementById('upload-form');
const progressBar = document.getElementById('progress-bar');
const progressBarFill = document.getElementById('progress-bar-fill');

// Existing event listener for simple processing
uploadForm.addEventListener('submit', function(event) {
    event.preventDefault();
    handleFileUpload('/upload'); // Use the existing /upload endpoint
});

// New event listener for advanced processing
const advancedButton = document.getElementById('advanced-button');
advancedButton.addEventListener('click', function(event) {
    event.preventDefault();
    handleFileUpload('/advanced_upload'); // Use the new /advanced_upload endpoint
});


// Function to handle file uploads
function handleFileUpload(endpoint) {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', endpoint, true);

        // Show progress bar
        progressBar.style.display = 'block';

        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressBarFill.style.width = percentComplete + '%';
            }
        };

        xhr.onload = function() {
            // Reset progress bar
            progressBarFill.style.width = '0%';
            progressBar.style.display = 'none';

            if (xhr.status === 200) {
                // Parse the JSON response
                const response = JSON.parse(xhr.responseText);
                if (response.message) {
                    alert(response.message);
                    // Optionally clear the file input
                    //fileInput.value = '';
                } else {
                    alert('An error occurred while processing the file.');
                }
            } else {
                // Handle errors
                const response = JSON.parse(xhr.responseText);
                alert(response.error || 'An error occurred during the upload.');
            }
        };

        xhr.onerror = function() {
            alert('An error occurred during the upload.');
            // Reset progress bar
            progressBarFill.style.width = '0%';
            progressBar.style.display = 'none';
        };

        xhr.send(formData);
    } else {
        alert('Please select a PDF file to upload.');
    }
}

// Handle question submission and display answer
function displayAnswer(answerText) {
    const answerDiv = document.getElementById('answer');
    answerDiv.innerHTML = ''; // Clear previous answer
    let i = 0;
    function typeWriter() {
        if (i < answerText.length) {
            answerDiv.innerHTML += answerText.charAt(i);
            i++;
            setTimeout(typeWriter, 20); // Adjust speed here
        }
    }
    typeWriter();
}

document.getElementById('question-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const question = document.getElementById('question-input').value;
    const processingMode = document.getElementById('processing-mode').value;

    fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question, processing_mode: processingMode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.answer) {
            displayAnswer(data.answer);
        } else if (data.error) {
            displayAnswer(data.error);
        } else {
            displayAnswer('No answer received.');
        }
    })
    .catch(error => {
        displayAnswer('Error: ' + error);
    });
});