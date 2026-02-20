# routes/main_routes.py

import datetime
from flask import render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import tiktoken
import faiss
import numpy as np
import pickle
from dotenv import load_dotenv
load_dotenv()
from promptlayer import PromptLayer
promptlayer_client = PromptLayer()
OpenAI = promptlayer_client.openai.OpenAI
client = OpenAI()

import re
import json
import sys
import traceback

SAFE_FILENAME_REGEX = re.compile(r'^[\w\-. ]+$')  # Letters, numbers, dash, underscore, dot, space

def is_safe_filename(filename):
    # Only allow .pdf extension and safe characters
    if not filename.lower().endswith('.pdf'):
        return False
    if not SAFE_FILENAME_REGEX.match(filename):
        return False
    # Prevent double extensions like .php.pdf, .js.pdf, etc.
    dangerous_exts = ['.php', '.js', '.exe', '.sh', '.bat', '.pl', '.py', '.rb', '.jsp', '.asp', '.html', '.htm']
    for ext in dangerous_exts:
        if ext + '.pdf' in filename.lower():
            return False
    # Prevent XSS in filename
    if '<' in filename or '>' in filename or '"' in filename or "'" in filename:
        return False
    return True

class MainRoutes:
    def __init__(self, app):
        self.app = app
        self.processed_files = set()
        self.processed_files_advanced = set()
        self.processed_documents = {}
        self.metadata_file = 'processed_documents.json'

        # Initialize or load id_to_text mapping FIRST
        if os.path.exists('id_to_text.pkl'):
            try:
                with open('id_to_text.pkl', 'rb') as f:
                    self.id_to_text = pickle.load(f)
            except Exception as e:
                print('Error loading id_to_text.pkl:', e)
                self.id_to_text = {}
        else:
            self.id_to_text = {}

        if os.path.exists('id_to_text_advanced.pkl'):
            try:
                with open('id_to_text_advanced.pkl', 'rb') as f:
                    self.id_to_text_advanced = pickle.load(f)
            except Exception as e:
                print('Error loading id_to_text_advanced.pkl:', e)
                self.id_to_text_advanced = {}
        else:
            self.id_to_text_advanced = {}

        self.vector_ids = list(self.id_to_text.keys())
        self.vector_ids_advanced = list(self.id_to_text_advanced.keys())

        # Vector ID -> document_id for contextual retrieval (which chunks belong to which doc)
        if os.path.exists('id_to_document_id.pkl'):
            try:
                with open('id_to_document_id.pkl', 'rb') as f:
                    self.id_to_document_id = pickle.load(f)
            except Exception as e:
                print('Error loading id_to_document_id.pkl:', e)
                self.id_to_document_id = {}
        else:
            self.id_to_document_id = {}
        if os.path.exists('id_to_document_id_advanced.pkl'):
            try:
                with open('id_to_document_id_advanced.pkl', 'rb') as f:
                    self.id_to_document_id_advanced = pickle.load(f)
            except Exception as e:
                print('Error loading id_to_document_id_advanced.pkl:', e)
                self.id_to_document_id_advanced = {}
        else:
            self.id_to_document_id_advanced = {}

        # Now safe to call load_processed_documents
        self.load_processed_documents()

        # One-time backfill: tie existing vectors to documents (for already-processed docs)
        self._backfill_id_to_document_id_if_needed()

        # Initialize or load FAISS index
        if os.path.exists('faiss_index.index'):
            try:
                self.faiss_index = faiss.read_index('faiss_index.index')
            except Exception as e:
                print('Error loading faiss_index.index:', e)
                self.faiss_index = None
        else:
            self.faiss_index = None

        # Advanced embeddings index
        if os.path.exists('faiss_index_advanced.index'):
            try:
                self.faiss_index_advanced = faiss.read_index('faiss_index_advanced.index')
            except Exception as e:
                print(f"Error loading advanced FAISS index: {e}")
                self.faiss_index_advanced = None
        else:
            self.faiss_index_advanced = None

    def load_processed_documents(self):
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    self.processed_documents = json.load(f)
            except Exception as e:
                print(f"Error loading processed_documents.json: {e}")
        else:
            # Backfill from FAISS mappings
            self.processed_documents = self.backfill_from_mappings()

    def _backfill_id_to_document_id_if_needed(self):
        """
        One-time backfill for already-processed documents: assign each vector to a document_id
        using the same heuristic as get_document_chunks, then save. So existing docs get
        their chunks tied together and context selection works without re-uploading.
        Only runs when the mapping file does not exist yet (first run after deploy).
        Runs at startup (batch); watch server logs for "Backfill..." messages.
        """
        need_backfill = any(
            id_to_text and not os.path.exists(pkl)
            for _, id_to_text, _, pkl in [
                (False, self.id_to_text, self.id_to_document_id, 'id_to_document_id.pkl'),
                (True, self.id_to_text_advanced, self.id_to_document_id_advanced, 'id_to_document_id_advanced.pkl'),
            ]
        )
        if need_backfill:
            print("[Backfill] Linking existing documents to chunks (one-time, at startup). Please wait...")
        total_updated = 0
        for advanced, id_to_text, id_to_doc, pkl_file in [
            (False, self.id_to_text, self.id_to_document_id, 'id_to_document_id.pkl'),
            (True, self.id_to_text_advanced, self.id_to_document_id_advanced, 'id_to_document_id_advanced.pkl'),
        ]:
            if not id_to_text or os.path.exists(pkl_file):
                continue
            processing = 'advanced' if advanced else 'simple'
            docs_for_mode = [d for d in self.processed_documents.values() if d.get('processing') == processing]
            if not docs_for_mode:
                continue
            updated = 0
            for doc in docs_for_mode:
                document_id = doc.get('id')
                title = doc.get('title') or ''
                filename = doc.get('filename') or ''
                filename_stem = os.path.splitext(filename)[0] if filename and filename != 'unknown' else ''
                title_prefix = (document_id or '').split('-')[0]
                for idx, text in id_to_text.items():
                    if not text:
                        continue
                    if title and title in text:
                        id_to_doc[idx] = document_id
                        updated += 1
                    elif title_prefix and title_prefix in text:
                        id_to_doc[idx] = document_id
                        updated += 1
                    elif filename_stem and filename_stem in text:
                        id_to_doc[idx] = document_id
                        updated += 1
            if updated:
                try:
                    with open(pkl_file, 'wb') as f:
                        pickle.dump(id_to_doc, f)
                    print(f"[Backfill] {processing}: linked {updated} chunk(s) to documents -> {pkl_file}")
                    total_updated += updated
                except Exception as e:
                    print(f"[Backfill] Error saving {pkl_file}: {e}")
        if need_backfill:
            print(f"[Backfill] Done. Total links: {total_updated}. You can use the app now.")

    def save_processed_documents(self):
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.processed_documents, f)
        except Exception as e:
            print(f"Error saving processed_documents.json: {e}")

    def backfill_from_mappings(self):
        docs = {}
        # Simple
        for idx, text in self.id_to_text.items():
            title = text[:40] if text else "unknown"
            date_str = "unknown"
            processing = "simple"
            doc_id = f"{title}-{processing}-{date_str}"
            docs[doc_id] = {
                "id": doc_id,
                "title": title,
                "date": date_str,
                "processing": processing,
                "filename": "unknown"
            }
        # Advanced
        for idx, text in self.id_to_text_advanced.items():
            title = text[:40] if text else "unknown"
            date_str = "unknown"
            processing = "advanced"
            doc_id = f"{title}-{processing}-{date_str}"
            docs[doc_id] = {
                "id": doc_id,
                "title": title,
                "date": date_str,
                "processing": processing,
                "filename": "unknown"
            }
        return docs

    def index(self):
        return render_template('index.html')

    def submit_prompt(self):
        # Your existing code for handling prompts
        pass

    def upload(self):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        # Security: Check for safe filename
        if not self.allowed_file(file.filename) or not is_safe_filename(file.filename):
            return jsonify({'error': 'Invalid or unsafe file name'}), 400
        filename = secure_filename(file.filename)
        upload_folder = self.app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        # Extract title (from filename or PDF)
        title = self.extract_title(file_path, filename)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        processing = "simple"
        document_id = f"{title}-{processing}-{date_str}"
        # Save metadata
        self.processed_documents[document_id] = {
            "id": document_id,
            "title": title,
            "date": date_str,
            "processing": processing,
            "filename": filename
        }
        self.save_processed_documents()
        # Process the file (e.g., extract text, generate embeddings)
        summary = self.summarize_document(file_path, is_pdf=True)
        self.summary = summary  # Store the summary

        # Check if file was already processed
        if summary == "File already processed":
            return jsonify({'message': 'File already processed'}), 200

        # Check summary before embedding
        if not summary or not summary.strip():
            return jsonify({'error': 'Could not extract text from PDF. Please upload a valid PDF with selectable text.'}), 400

        # Generate embedding for the summary
        try:
            embedding = self.get_embedding(summary)
            print('Embedding genenerated')
            self.save_embedding(embedding, summary, document_id=document_id)
            print('Embedding saved')
        except Exception as e:
            print(f"Error during embedding or saving: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
        return jsonify({'message': 'File successfully uploaded and processed'}), 200

    def advanced_upload(self):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        # Security: Check for safe filename
        if not self.allowed_file(file.filename) or not is_safe_filename(file.filename):
            return jsonify({'error': 'Invalid or unsafe file name'}), 400
        filename = secure_filename(file.filename)
        upload_folder = self.app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        # Extract title (from filename or PDF)
        title = self.extract_title(file_path, filename)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        processing = "advanced"
        document_id = f"{title}-{processing}-{date_str}"
        # Save metadata
        self.processed_documents[document_id] = {
            "id": document_id,
            "title": title,
            "date": date_str,
            "processing": processing,
            "filename": filename
        }
        self.save_processed_documents()
        # Process the document using advanced processing
        self.summarize_document(file_path, is_pdf=True, advanced=True, document_id=document_id)
        return jsonify({'message': 'File successfully uploaded and processed with advanced processing'}), 200

    def ask(self):
        try:
            data = request.get_json()
            document_id = data.get('document_id')
            question = data.get('question', '')
            processing_mode = data.get('processing_mode', 'simple')
            print('Now asking...')

            if not question:
                return jsonify({'error': 'No question provided'}), 400
            if not (document_id and str(document_id).strip()):
                return jsonify({'error': 'Please select a document (context) for your question.'}), 400

            # Document and answering method must match (safety check if frontend is bypassed)
            doc_meta = self.processed_documents.get(document_id)
            if doc_meta and doc_meta.get('processing') != processing_mode:
                return jsonify({
                    'error': f"This document was processed with {doc_meta['processing'].title()}. "
                             f"Use the {doc_meta['processing'].title()} answering method (it is set automatically when you select the document)."
                }), 400

            # Generate embedding for the question
            question_embedding = self.get_embedding(question)
            print('Question Embedding Generated')

            # Select the appropriate index and mappings
            if processing_mode == 'advanced':
                index = self.faiss_index_advanced
                id_to_text = self.id_to_text_advanced
                print('Advanced Question')
                if index is None or index.ntotal == 0:
                    index = self.load_faiss_index('faiss_index_advanced.index')
                    self.faiss_index_advanced = index
                    id_to_text = self.load_id_to_text('id_to_text_advanced.pkl')
                    self.id_to_text_advanced = id_to_text
                print({index.ntotal})
            else:
                index = self.faiss_index
                id_to_text = self.id_to_text
                print('Simple Question')
                print({index.ntotal})

            # Check if the index has embeddings
            if index is None or index.ntotal == 0:
                return jsonify({'error': 'The knowledge base is empty for the selected processing mode. Please upload and process a document first.'}), 400
            print('Similar Embedding Found')

            # Get chunk IDs and texts for the selected document only
            chunk_pairs = self.get_document_chunks(document_id, processing_mode)
            chunk_ids = [idx for idx, _ in chunk_pairs]
            if not chunk_ids:
                return jsonify({'error': 'No chunks found for the selected document.'}), 400

            chunk_id_set = set(chunk_ids)
            top_k_retrieve = 5
            # Search more candidates then filter to this document's chunks (FAISS has no "search in subset")
            search_k = min(100, index.ntotal)
            D, I = index.search(np.array([question_embedding], dtype='float32'), search_k)
            # Keep only results that belong to the selected document
            I_filtered = [idx for idx in I[0] if idx != -1 and idx in chunk_id_set]
            # Take top 5 by similarity (already ordered by D)
            if I_filtered:
                contexts = [id_to_text[idx] for idx in I_filtered[:top_k_retrieve]]
            else:
                # No hits in top search_k from this doc (rare); use doc's chunks in order
                contexts = [text for _, text in chunk_pairs[:top_k_retrieve]]
            print('Similar Embedding Searching (context filtered to selected document)')

            # Construct the prompt
            prompt = self.construct_prompt(question, contexts)

            # Generate the answer
            answer = self.generate_answer_from_prompt(prompt)
            print('Answer Found')

            # Return as JSON for consistency
            return jsonify({'answer': answer}), 200

        except Exception as e:
            err_msg = str(e)
            tb = traceback.format_exc()
            # Unmissable log block so you see the real error in the terminal
            print("\n" + "=" * 60, file=sys.stderr)
            print("POST /ask FAILED (500)", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(f"Error: {err_msg}", file=sys.stderr)
            print("\nFull traceback:", file=sys.stderr)
            print(tb, file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
            return jsonify({'error': err_msg}), 500


    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

    # Utility Functions

    def summarize_document(self, file_path, is_pdf=False, advanced=False, document_id=None):
        """
        Generates a summary of a text or PDF document.
        Args:
            file_path (str): Path to the document.
            is_pdf (bool, optional): Flag to indicate if the document is a PDF. Defaults to False.
            advanced (bool): If True, chunk and embed full text; else summarize and embed summary.
            document_id (str|None): Document ID to tie chunks/summary to (for context retrieval).
        Returns:
            str: Summary of the document.
        """
        if is_pdf:
            content = self.pdf_to_text(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        
        if advanced:
            # Advanced processing: Generate embeddings from full text
            chunks = self.split_text_into_chunks(content)
            for chunk in chunks:
                embedding = self.get_embedding(chunk)
                self.save_embedding(embedding, chunk, advanced=True, document_id=document_id)
                print('Advanced Save Just Happened')
        
        else:
            # Simple processing: Generate summary and embeddings
            if len(content) > 4000:
                summary = self.summarize_large_content(content)
                print('Simple Large Save Just Happened')
            else:
                summary = self.generate_summary(content)
                print('Simple Small Save Just Happened')
    
            print('Document Summary:\n', summary)
        
        # Generate a unique identifier for the file
        file_hash = self.get_file_hash(file_path)

        # Check if the file has already been processed
        if advanced:
            if file_hash in self.processed_files_advanced:
                print("File already processed with advanced processing.")
                return "File already processed"
        else:
            if file_hash in self.processed_files:
                print("File already processed with simple processing.")
                return "File already processed"
        # You can store the summary for later use

            # Add to processed files
        if advanced:
            self.processed_files_advanced.add(file_hash)
        else:
            self.processed_files.add(file_hash)


            self.summary = summary  # Storing the summary in an instance variable
            return summary

    def get_file_hash(self, file_path):
        try:
            import hashlib
            BUF_SIZE = 65536  # Read in 64kb chunks
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(BUF_SIZE)
                    if not data:
                        break
                    sha256.update(data)
            return sha256.hexdigest()
        except Exception as e:
            print(f"Error generating file hash: {e}")
            return ""

    def pdf_to_text(self, pdf_path):
        try:
            """
            Converts a PDF file to text.
            Args:
                pdf_path (str): Path to the PDF file.
            Returns:
                str: Extracted text from the PDF file.
            """
            reader = PdfReader(pdf_path)
            extracted_texts = [page.extract_text() for page in reader.pages]
            return ' '.join(extracted_texts).replace('\n', ' ')
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def summarize_large_content(self, content):
        """
        Generates a summary for large content.
        Args:
            content (str): Large content to be summarized.
        Returns:
            str: Summary of the large content.
        """
        chunks = self.split_text_into_chunks(content)
        chunk_summaries = [self.generate_summary(chunk) for chunk in chunks]
        combined_text = ' '.join(chunk_summaries)
        return self.generate_summary(combined_text)

    def split_text_into_chunks(self, text, chunk_size=3000):
        try:
            """
            Splits text into smaller chunks.
            Args:
                text (str): Text to be split.
                chunk_size (int, optional): Size of each chunk. Defaults to 3000.
            Returns:
                list[str]: List of text chunks.
            """
            tokens = self.encode_text(text)
            chunks = []
            for i in range(0, len(tokens), chunk_size):
                chunk = self.decode_tokens(tokens[i:i + chunk_size])
                chunks.append(chunk)
            return chunks
        except Exception as e:
            print(f"Error splitting text into chunks: {e}")
            return []

    def generate_summary(self, text):
        try:
            """
            Generates a summary of the provided text using the OpenAI GPT-3.5 Turbo model.
            Args:
                text (str): Text to be summarized.
            Returns:
                str: Summary of the text.
            """
            prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.5
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return ""

    def generate_answer(self, question):
        try:
            """
            Generates an answer to the user's question using the stored summary.
            Args:
                question (str): The user's question.
            Returns:
                str: Answer to the question.
            """
            if hasattr(self, 'summary'):
                context = self.summary
            else:
                context = "No context available. Please upload and process a document first."
                return context

            prompt = f"Answer the following question based on the provided context.\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.5
            )
            answer = response.choices[0].message.content.strip()
            return answer
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "Sorry, an error occurred while generating the answer."
    
    def get_embedding(self, text):
        try:
            """
            Generates an embedding for the given text using OpenAI's Embeddings API.
            
            Args:
                text (str): The text to generate an embedding for.
            
            Returns:
                np.ndarray: The embedding vector as a NumPy array.
            """
            response = client.embeddings.create(
                input=text,
                model='text-embedding-ada-002'  # Latest embedding model as of 2023
            )

            embedding = response.data[0].embedding
            return np.array(embedding, dtype='float32')
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def create_faiss_index(self, embeddings, ids):
        """
        Creates a FAISS index from the provided embeddings.
        
        Args:
            embeddings (np.ndarray): A 2D NumPy array of embeddings.
            ids (List[int]): A list of IDs corresponding to each embedding.
        
        Returns:
            faiss.IndexFlatL2: The FAISS index.
        """
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add_with_ids(embeddings, np.array(ids))
        return index
    
    def save_embedding(self, embedding, text, advanced=False, document_id=None):
        try:
            """
            Saves the embedding and associated text into the FAISS index.
            Optionally ties this vector to a document_id for contextual retrieval.

            Args:
                embedding (np.ndarray): The embedding vector.
                text (str): The text corresponding to the embedding.
                advanced (bool): Use advanced index/mappings.
                document_id (str|None): Document this chunk/summary belongs to (for context filtering).
            """
            if advanced:
                # Use separate index and mappings for advanced processing
                if self.faiss_index_advanced is None:
                    print("Initializing advanced FAISS index.")
                    dimension = embedding.shape[0]
                    self.faiss_index_advanced = faiss.IndexFlatL2(dimension)
                    self.faiss_index_advanced = faiss.IndexIDMap(self.faiss_index_advanced)
                    self.vector_ids_advanced = []
                    self.id_to_text_advanced = {}
                index = self.faiss_index_advanced
                vector_ids = self.vector_ids_advanced
                id_to_text = self.id_to_text_advanced
                id_to_doc = self.id_to_document_id_advanced
                index_file = 'faiss_index_advanced.index'
                mapping_file = 'id_to_text_advanced.pkl'
                doc_mapping_file = 'id_to_document_id_advanced.pkl'
            else:
                if self.faiss_index is None:
                    # Initialize the index if it doesn't exist
                    dimension = embedding.shape[0]
                    self.faiss_index = faiss.IndexFlatL2(dimension)
                    self.faiss_index = faiss.IndexIDMap(self.faiss_index)
                    self.vector_ids = []
                    self.id_to_text = {}
                index = self.faiss_index
                vector_ids = self.vector_ids
                id_to_text = self.id_to_text
                id_to_doc = self.id_to_document_id
                index_file = 'faiss_index.index'
                mapping_file = 'id_to_text.pkl'
                doc_mapping_file = 'id_to_document_id.pkl'

            # Generate a unique ID for the embedding
            vector_id = len(vector_ids)
            vector_ids.append(vector_id)

            # Add the embedding to the index
            embedding = np.array([embedding], dtype='float32')
            index.add_with_ids(embedding, np.array([vector_id], dtype='int64'))

            # Store the text with the corresponding ID
            id_to_text[vector_id] = text

            # Tie this vector to the document for context filtering
            if document_id is not None:
                id_to_doc[vector_id] = document_id

            # Save the index and mappings
            faiss.write_index(index, index_file)
            with open(mapping_file, 'wb') as f:
                pickle.dump(id_to_text, f)
            if document_id is not None:
                with open(doc_mapping_file, 'wb') as f:
                    pickle.dump(id_to_doc, f)
            print(f"Added embedding with ID {vector_id} to {'advanced' if advanced else 'simple'} FAISS index."
                  + (f" document_id={document_id}" if document_id else ""))
        except Exception as e:
            print(f"Error saving embedding or index: {e}")

    def get_processed_documents(self):
        # Reload from disk so all workers (e.g. gunicorn -w 4) return the latest list.
        # Otherwise the upload worker updates the file but other workers still have stale in-memory data.
        self.load_processed_documents()
        out = []
        for doc in self.processed_documents.values():
            d = dict(doc)
            d.setdefault('display_name', None)
            out.append(d)
        return jsonify(out)

    def update_document(self):
        """Update display_name (or title) for a document so users can set a recognizable label."""
        try:
            data = request.get_json() or {}
            document_id = data.get('document_id')
            display_name = data.get('display_name', '').strip() or None
            if not document_id:
                return jsonify({'error': 'document_id required'}), 400
            if document_id not in self.processed_documents:
                return jsonify({'error': 'Document not found'}), 404
            self.processed_documents[document_id]['display_name'] = display_name
            self.save_processed_documents()
            return jsonify(self.processed_documents[document_id]), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    
    def construct_prompt(self, question, contexts):
        """
        Constructs a prompt for the language model using the question and retrieved contexts.
        
        Args:
            question (str): The user's question.
            contexts (List[str]): A list of context texts.
        
        Returns:
            str: The constructed prompt.
        """
        context_text = "\n\n".join(contexts)
        prompt = f"""You are an AI assistant that answers questions based only on the information provided in the context below. If you cannot find the answer in the context, politely inform the user that you cannot answer based on the provided information.

    Context:
    {context_text}

    Question:
    {question}

    Answer:"""
        return prompt

    def generate_answer_from_prompt(self, prompt):
        try:
            """
            Generates an answer using OpenAI's ChatCompletion API.
            
            Args:
                prompt (str): The prompt to send to the API.
            
            Returns:
                str: The generated answer.
            """
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.5
            )
            answer = response.choices[0].message.content.strip()
            return answer
        except Exception as e:
            print(f"Error generating answer from prompt: {e}")
            return "Sorry, an error occurred while generating the answer."
    
    

    # Helper methods to handle tokens
    def encode_text(self, text):
        encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
        return encoding.encode(text)

    def decode_tokens(self, tokens):
        encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
        return encoding.decode(tokens)
    
    def load_faiss_index(self, index_file):
        if os.path.exists(index_file):
            try:
                index = faiss.read_index(index_file)
                print(f"Loaded FAISS index from {index_file}.")
                return index
            except Exception as e:
                print(f"Error loading FAISS index from {index_file}: {e}")
                return None
        else:
            print(f"FAISS index file {index_file} does not exist.")
            return None

    def load_id_to_text(self, mapping_file):
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'rb') as f:
                    id_to_text = pickle.load(f)
                print(f"Loaded id_to_text mapping from {mapping_file}.")
                return id_to_text
            except Exception as e:
                print(f"Error loading id_to_text mapping from {mapping_file}: {e}")
                return {}
        else:
            print(f"id_to_text mapping file {mapping_file} does not exist.")
            return {}
        
    def extract_title(self, file_path, filename):
        # Try to extract from PDF, fallback to filename (without extension)
        try:
            reader = PdfReader(file_path)
            first_page = reader.pages[0]
            text = first_page.extract_text()
            if text:
                # Use first non-empty line as title
                for line in text.splitlines():
                    if line.strip():
                        return line.strip()
        except Exception:
            pass
        # Fallback: filename without extension
        return os.path.splitext(filename)[0]
    
    def get_document_chunks(self, document_id, processing_mode):
        """
        Retrieve all chunk IDs and texts for a given document_id and processing mode.
        Uses stored id_to_document_id when available; falls back to title heuristic for legacy data.
        Returns a list of (chunk_id, chunk_text).
        """
        if processing_mode == "advanced":
            id_to_text = self.id_to_text_advanced
            id_to_doc = self.id_to_document_id_advanced
        else:
            id_to_text = self.id_to_text
            id_to_doc = self.id_to_document_id

        # Prefer explicit vector -> document_id mapping (set for new uploads)
        if id_to_doc:
            chunk_ids = [idx for idx, doc_id in id_to_doc.items() if doc_id == document_id]
            if chunk_ids:
                return [(idx, id_to_text[idx]) for idx in chunk_ids if idx in id_to_text]
        # Fallback: heuristic for legacy data (no id_to_document_id or doc not in mapping)
        doc_meta = self.processed_documents.get(document_id)
        if not doc_meta:
            return []
        title = doc_meta.get("title") or ""
        filename = doc_meta.get("filename") or ""
        filename_stem = os.path.splitext(filename)[0] if filename and filename != "unknown" else ""
        title_prefix = (document_id or "").split("-")[0]
        matched_chunks = []
        for idx, text in id_to_text.items():
            if not text:
                continue
            if title and title in text:
                matched_chunks.append((idx, text))
            elif title_prefix and title_prefix in text:
                matched_chunks.append((idx, text))
            elif filename_stem and filename_stem in text:
                matched_chunks.append((idx, text))
        return matched_chunks