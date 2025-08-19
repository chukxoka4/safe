// Handle file upload and progress bar
const uploadForm = document.getElementById('upload-form');
const progressBar = document.getElementById('progress-bar');
const progressBarFill = document.getElementById('progress-bar-fill');

uploadForm.addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent default form submission

    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        // Show progress bar
        progressBar.style.display = 'block';

        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressBarFill.style.width = percentComplete + '%';
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                alert('File uploaded and processed successfully.');
                // Reset progress bar
                progressBarFill.style.width = '0%';
                progressBar.style.display = 'none';
            } else {
                alert('An error occurred during the upload.');
            }
        };

        xhr.onerror = function() {
            alert('An error occurred during the upload.');
        };

        xhr.send(formData);
    } else {
        alert('Please select a PDF file to upload.');
    }
});

// Handle question submission and display answer
const questionForm = document.getElementById('question-form');
const answerDiv = document.getElementById('answer');

questionForm.addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent default form submission

    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();

    if (question) {
        // Create a POST request to send the question to the server
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/ask', true);
        xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');

        xhr.onload = function() {
            if (xhr.status === 200) {
                // Display the answer
                answerDiv.textContent = xhr.responseText;
            } else {
                answerDiv.textContent = 'An error occurred while retrieving the answer.';
            }
        };

        xhr.onerror = function() {
            answerDiv.textContent = 'An error occurred while retrieving the answer.';
        };

        // Send the question as JSON
        xhr.send(JSON.stringify({ question: question }));
    } else {
        alert('Please enter a question.');
    }
});