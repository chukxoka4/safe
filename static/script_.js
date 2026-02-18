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

// Build a recognizable label: custom name > filename > auto title
function docLabel(doc) {
  if (doc.display_name) return doc.display_name;
  if (doc.filename && doc.filename !== 'unknown') return doc.filename;
  return doc.title || doc.id;
}

function setDocumentContextReady(ready, message) {
  const statusEl = document.getElementById('document-context-status');
  const selectEl = document.getElementById('document-select');
  if (!statusEl || !selectEl) return;
  if (ready) {
    statusEl.textContent = '';
    statusEl.style.display = 'none';
    selectEl.style.display = '';
  } else {
    statusEl.textContent = message || 'Preparing document context…';
    statusEl.style.display = '';
    selectEl.style.display = 'none';
  }
}

function refreshDocumentDropdown() {
  setDocumentContextReady(false, 'Loading document list…');
  fetch('/processed_documents')
    .then(res => res.json())
    .then(docs => {
      window._lastDocList = docs;
      const select = document.getElementById('document-select');
      const currentValue = select.value;
      select.innerHTML = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '— Select document (context for your question) —';
      select.appendChild(placeholder);
      docs.forEach(doc => {
        const option = document.createElement('option');
        option.value = doc.id;
        option.textContent = `${docLabel(doc)} (${doc.date}) [${doc.processing}]`;
        select.appendChild(option);
      });
      if (currentValue) select.value = currentValue;
      updateDisplayNameField();
      setDocumentContextReady(true);
    })
    .catch(function() {
      setDocumentContextReady(false, 'Could not load documents. Retrying…');
    });
}

function updateDisplayNameField() {
  const select = document.getElementById('document-select');
  const input = document.getElementById('document-display-name');
  const id = select.value;
  if (!id) { input.value = ''; input.placeholder = 'Select a document first'; return; }
  input.placeholder = 'e.g. Course Notes Unit 1';
  const doc = (window._lastDocList || []).find(d => d.id === id);
  input.value = doc ? (doc.display_name || '') : '';
}

// Initial load (shows "Preparing document context…" until server is ready; backfill runs at server startup)
setDocumentContextReady(false, 'Preparing document context…');
fetch('/processed_documents')
  .then(res => res.json())
  .then(docs => {
    window._lastDocList = docs;
    const select = document.getElementById('document-select');
    select.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— Select document (context for your question) —';
    select.appendChild(placeholder);
    docs.forEach(doc => {
      const option = document.createElement('option');
      option.value = doc.id;
      option.textContent = `${docLabel(doc)} (${doc.date}) [${doc.processing}]`;
      select.appendChild(option);
    });
    select.addEventListener('change', updateDisplayNameField);
    updateDisplayNameField();
    setDocumentContextReady(true);
  })
  .catch(function() {
    setDocumentContextReady(false, 'Could not load documents. Is the server running?');
  });

// Save display name for selected document
document.getElementById('save-display-name').addEventListener('click', function() {
  const documentId = document.getElementById('document-select').value;
  const displayName = document.getElementById('document-display-name').value.trim();
  if (!documentId) { alert('Select a document first.'); return; }
  fetch('/update_document', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, display_name: displayName || null })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) { alert(data.error); return; }
      if (window._lastDocList) {
        const doc = window._lastDocList.find(d => d.id === documentId);
        if (doc) doc.display_name = displayName || null;
      }
      refreshDocumentDropdown();
      document.getElementById('document-display-name').value = displayName;
    })
    .catch(() => alert('Failed to save name.'));
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
                    refreshDocumentDropdown(); // so new document appears in context dropdown
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
    const documentId = document.getElementById('document-select').value;

    fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, processing_mode: processingMode, document_id: documentId })
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