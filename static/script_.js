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
  const wrapperEl = document.getElementById('doc-select-wrapper');
  if (!statusEl || !wrapperEl) return;
  if (ready) {
    statusEl.textContent = '';
    statusEl.style.display = 'none';
    wrapperEl.style.display = '';
  } else {
    statusEl.textContent = message || 'Preparing document context…';
    statusEl.style.display = '';
    wrapperEl.style.display = 'none';
  }
}

var DOC_LABEL_MAX = 60;
function getDocOptionLabel(doc) {
  var full = docLabel(doc) + ' (' + doc.date + ') [' + doc.processing + ']';
  var short = full.length > DOC_LABEL_MAX ? full.slice(0, DOC_LABEL_MAX - 3) + '…' : full;
  return { full: full, short: short };
}

function renderDocList(docs) {
  var listEl = document.getElementById('doc-select-list');
  var hiddenInput = document.getElementById('document-select');
  var currentId = hiddenInput && hiddenInput.value ? hiddenInput.value : '';
  if (!listEl) return;
  listEl.innerHTML = '';
  docs.forEach(function(doc) {
    var labels = getDocOptionLabel(doc);
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'doc-select-option';
    btn.setAttribute('role', 'option');
    btn.setAttribute('aria-selected', doc.id === currentId ? 'true' : 'false');
    btn.setAttribute('data-id', doc.id);
    btn.setAttribute('data-full-label', labels.full);
    btn.title = labels.full;
    btn.textContent = labels.short;
    listEl.appendChild(btn);
  });
}

function filterDocList(searchText) {
  var listEl = document.getElementById('doc-select-list');
  if (!listEl) return;
  var q = (searchText || '').toLowerCase().trim();
  var opts = listEl.querySelectorAll('.doc-select-option');
  var visible = 0;
  opts.forEach(function(opt) {
    var label = (opt.getAttribute('data-full-label') || opt.textContent || '').toLowerCase();
    var show = !q || label.indexOf(q) !== -1;
    opt.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  var noEl = listEl.querySelector('.doc-select-no-results');
  if (visible === 0 && opts.length) {
    if (!noEl) {
      noEl = document.createElement('div');
      noEl.className = 'doc-select-no-results';
      noEl.textContent = 'No documents match.';
      listEl.appendChild(noEl);
    }
    noEl.style.display = '';
  } else if (noEl) noEl.style.display = 'none';
}

function setDocSelectTriggerText(text) {
  var trigger = document.getElementById('doc-select-trigger');
  if (trigger) trigger.textContent = text || '— Select document (context for your question) —';
}

function openDocSelectPanel() {
  var panel = document.getElementById('doc-select-panel');
  var trigger = document.getElementById('doc-select-trigger');
  if (panel && trigger) {
    panel.classList.add('is-open');
    panel.setAttribute('aria-hidden', 'false');
    trigger.setAttribute('aria-expanded', 'true');
    var searchEl = document.getElementById('doc-select-search');
    if (searchEl) { searchEl.value = ''; searchEl.focus(); filterDocList(''); }
  }
}

function closeDocSelectPanel() {
  var panel = document.getElementById('doc-select-panel');
  var trigger = document.getElementById('doc-select-trigger');
  if (panel && trigger) {
    panel.classList.remove('is-open');
    panel.setAttribute('aria-hidden', 'true');
    trigger.setAttribute('aria-expanded', 'false');
  }
}

function initDocSelect() {
  var wrapper = document.getElementById('doc-select-wrapper');
  var trigger = document.getElementById('doc-select-trigger');
  var panel = document.getElementById('doc-select-panel');
  var searchEl = document.getElementById('doc-select-search');
  var listEl = document.getElementById('doc-select-list');
  var hiddenInput = document.getElementById('document-select');
  if (!wrapper || !trigger || !panel || !listEl || !hiddenInput) return;

  trigger.addEventListener('click', function(e) {
    e.preventDefault();
    if (panel.classList.contains('is-open')) closeDocSelectPanel();
    else openDocSelectPanel();
  });

  searchEl && searchEl.addEventListener('input', function() { filterDocList(this.value); });
  searchEl && searchEl.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeDocSelectPanel(); trigger.focus(); }
  });

  listEl.addEventListener('click', function(e) {
    var opt = e.target.closest('.doc-select-option');
    if (!opt) return;
    var id = opt.getAttribute('data-id');
    var fullLabel = opt.getAttribute('data-full-label');
    hiddenInput.value = id || '';
    setDocSelectTriggerText(fullLabel);
    listEl.querySelectorAll('.doc-select-option').forEach(function(o) {
      o.setAttribute('aria-selected', o.getAttribute('data-id') === id ? 'true' : 'false');
    });
    closeDocSelectPanel();
    updateDisplayNameField();
    syncProcessingModeToDocument();
  });

  document.addEventListener('click', function(e) {
    if (panel.classList.contains('is-open') && !wrapper.contains(e.target))
      closeDocSelectPanel();
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && panel.classList.contains('is-open')) {
      closeDocSelectPanel();
      trigger.focus();
    }
  });
}

function refreshDocumentDropdown() {
  setDocumentContextReady(false, 'Loading document list…');
  fetch('/processed_documents')
    .then(res => res.json())
    .then(docs => {
      window._lastDocList = docs;
      var hiddenInput = document.getElementById('document-select');
      var currentValue = hiddenInput ? hiddenInput.value : '';
      renderDocList(docs);
      if (currentValue && docs.some(function(d) { return d.id === currentValue; })) {
        hiddenInput.value = currentValue;
        var doc = docs.find(function(d) { return d.id === currentValue; });
        if (doc) setDocSelectTriggerText(getDocOptionLabel(doc).full);
      } else {
        hiddenInput.value = '';
        setDocSelectTriggerText('');
      }
      updateDisplayNameField();
      syncProcessingModeToDocument();
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

// Keep answering method in sync with selected document (simple doc → Simple, advanced doc → Advanced).
// Dropdown is read-only when a document is selected so it always matches.
function syncProcessingModeToDocument() {
  const select = document.getElementById('document-select');
  const modeSelect = document.getElementById('processing-mode');
  if (!modeSelect) return;
  const id = select.value;
  if (!id) { modeSelect.value = 'simple'; modeSelect.disabled = true; return; }
  const doc = (window._lastDocList || []).find(d => d.id === id);
  if (doc && doc.processing) {
    modeSelect.value = doc.processing;
    modeSelect.disabled = true;  // read-only: must match document, no mismatch possible
  }
}

// Initial load (shows "Preparing document context…" until server is ready; backfill runs at server startup)
setDocumentContextReady(false, 'Preparing document context…');
fetch('/processed_documents')
  .then(res => res.json())
  .then(docs => {
    window._lastDocList = docs;
    renderDocList(docs);
    initDocSelect();
    updateDisplayNameField();
    syncProcessingModeToDocument();
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

// Handle question submission and display answer. onComplete() runs when typewriter finishes.
function displayAnswer(answerText, onComplete) {
    const answerDiv = document.getElementById('answer');
    answerDiv.innerHTML = '';
    let i = 0;
    function typeWriter() {
        if (i < answerText.length) {
            answerDiv.innerHTML += answerText.charAt(i);
            i++;
            setTimeout(typeWriter, 20);
        } else {
            if (typeof onComplete === 'function') onComplete();
        }
    }
    typeWriter();
}

function setAskBusy(busy) {
    var btn = document.getElementById('ask-button');
    var loading = document.getElementById('ask-loading');
    if (!btn || !loading) return;
    btn.disabled = !!busy;
    loading.style.display = busy ? 'inline' : 'none';
}

document.getElementById('question-form').addEventListener('submit', function(e) {
    e.preventDefault();
    var question = document.getElementById('question-input').value;
    var processingMode = document.getElementById('processing-mode').value;
    var documentId = document.getElementById('document-select').value;

    setAskBusy(true);

    fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, processing_mode: processingMode, document_id: documentId })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        var text = data.answer || data.error || 'No answer received.';
        displayAnswer(text, function() { setAskBusy(false); });
    })
    .catch(function(error) {
        displayAnswer('Error: ' + error, function() { setAskBusy(false); });
    });
});

// Theme toggle: dark (default) / light, persisted in localStorage
(function() {
  var KEY = 'safe-ai-theme';
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (!btn) return;
  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (theme === 'light') {
      btn.textContent = 'Dark';
      btn.setAttribute('aria-label', 'Switch to dark theme');
    } else {
      btn.textContent = 'Light';
      btn.setAttribute('aria-label', 'Switch to light theme');
    }
    try { localStorage.setItem(KEY, theme); } catch (e) {}
  }
  function initTheme() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === 'light' || saved === 'dark') applyTheme(saved);
      else applyTheme('dark');
    } catch (e) { applyTheme('dark'); }
  }
  initTheme();
  btn.addEventListener('click', function() {
    var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    applyTheme(next);
  });
})();