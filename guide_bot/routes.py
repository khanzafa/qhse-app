# guide_bot/routes.py
import getpass
import io
import re
from uuid import uuid4
from flask import Blueprint, abort, render_template, redirect, send_file, url_for, flash, request, session
from langchain_chroma import Chroma
import markdown
from guide_bot.models import Document
from guide_bot.forms import DocumentForm
from app import db
from PyPDF2 import PdfReader
import docx2txt
from pptx import Presentation
import win32com.client
import pythoncom
import pandas
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import bcrypt
from langchain_core.documents import Document as ChatDocument
from werkzeug.utils import secure_filename
from guide_bot import conversation_chat, create_conversational_chain, load_vector_store, save_uploaded_file, load_saved_files, split_documents

guide_bot = Blueprint('guide_bot', __name__)

GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')

# Don't forget to update the manage_documents route to save documents with their ids
@guide_bot.route('/guide-bot/documents', methods=['GET', 'POST'])
def manage_documents():
    form = DocumentForm()
    documents = Document.query.all()
    # file = form.file.data
    files = request.files.getlist('files')
    if form.validate_on_submit():
        for file in files:
            filename = secure_filename(file.filename)
            # Save new document to the database
            new_document = Document(
                title=filename,
                file=file.read()
            )
            db.session.add(new_document)
            db.session.commit()

            # Save document to disk
            save_dir = 'data'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            file_path = os.path.join(save_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(new_document.file)

        flash('Document added successfully and vector store updated!')
        return redirect(url_for('guide_bot.manage_documents'))

    return render_template('guide_bot/manage_documents.html', form=form, documents=documents)

@guide_bot.route('/guide-bot/documents/edit/<int:id>', methods=['GET', 'POST'])
def edit_document(id):
    document = Document.query.get_or_404(id)
    form = DocumentForm(obj=document)

    if form.validate_on_submit():
        document.title = form.title.data
        document.file = form.file.data.read()
        db.session.commit()
        flash('Document updated successfully!')
        return redirect(url_for('guide_bot.manage_documents'))

    return render_template('guide_bot/edit_document.html', form=form, document=document)

@guide_bot.route('/guide-bot/documents/delete/<int:id>', methods=['POST'])
def delete_document(id):
    document = Document.query.get_or_404(id)
    
    # Delete the document from the database
    db.session.delete(document)
    db.session.commit()

    # delete the file from the server
    file_path = os.path.join('data', secure_filename(document.title))
    if os.path.exists(file_path):
        os.remove(file_path)
    
    flash('Document deleted successfully, and vector store updated!')
    return redirect(url_for('guide_bot.manage_documents'))

@guide_bot.route('/guide-bot/documents/view/<int:id>')
def view_document(id):
    document = Document.query.get_or_404(id)
    return render_template('guide_bot/view_document.html', document=document)

@guide_bot.route('/guide-bot/document/file/<int:document_id>')
def get_document_file(document_id):
    document = Document.query.get_or_404(document_id)
    if document.file:
        # Determine the MIME type based on the file extension
        file_extension = os.path.splitext(document.title)[1].lower()
        if file_extension == '.pdf':
            mimetype = 'application/pdf'
            as_attachment = False  # View PDF in the browser
        elif file_extension in ['.doc', '.docx']:
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            as_attachment = True  # Force download for Word files
        elif file_extension in ['.xls', '.xlsx']:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            as_attachment = True  # Force download for Excel files
        else:
            # For unsupported file types, return a 404 error
            abort(404)

        return send_file(io.BytesIO(document.file), mimetype=mimetype, as_attachment=as_attachment, download_name=document.title)
    else:
        abort(404)

@guide_bot.route('/guide-bot/documents/download/<int:id>')
def download_document(id):
    document = Document.query.get_or_404(id)
    return send_file(io.BytesIO(document.file), as_attachment=True, download_name=document.title)

# Initialize variables
history = []
generated = ["Selamat datang di GuideBot! Tanyakan sesuatu pada saya 😊️"]
past = []

@guide_bot.route('/guide-bot/chat', methods=['GET', 'POST'])
def chat():
    global history, generated, past

    if request.method == 'POST':
        user_input = request.form['user_input']        
        vector_store = load_vector_store(embeddings)
        print("Vector store loaded")
        if vector_store:
            print("Vector store is not empty")
            chain = create_conversational_chain(vector_store)
            print("Conversational chain created")
            print("History:", history)
            output, source_documents = conversation_chat(user_input, chain, history)
            print("Output:", output)
            print("Conversation completed"  )
            past.append(user_input)
            generated.append({
                "message": output,
                "source_documents": source_documents
            })
        else:
            flash('⚠️ No documents uploaded by admin yet.', 'warning')

    return render_template('guide_bot/index.html', past=past, generated=generated)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'})

@guide_bot.route('/guide-bot/reload-vector-db', methods=['GET'])
def reload_vector_db():
    vector_store = Chroma(
        collection_name="SPIL",
        embedding_function=embeddings or HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'}), 
        persist_directory="vector_store"
    )
    # Load all documents from the SQL database
    documents = Document.query.all()
    document_ids = [str(document.id) for document in documents]    
    vector_store_ids = vector_store.get()['ids']    
    vector_metadatas = vector_store.get()['metadatas']
    print("Documents:", document_ids)    
    print("Vector store IDs:", vector_store_ids)

    # Prepare documents for vector store
    for document in documents:
        vector_store_ids = vector_store.get()['ids']
        print("Vector store IDs:", vector_store_ids)
        # Check if document already exists in the vector store
        if str(document.id) in vector_store_ids:
            continue           

        file_path = os.path.join('data', secure_filename(document.title))
        
        # Extract text based on file type
        all_text = ""
        if file_path.endswith('.pdf'):
            pdf_reader = PdfReader(file_path)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    all_text += text
        elif file_path.endswith('.docx'):
            all_text = docx2txt.process(file_path)        
        elif file_path.endswith('.ods') or file_path.endswith('.xls') or file_path.endswith('.xlsx'):
            df = pandas.read_excel(file_path)
            all_text = df.to_string()
        elif file_path.endswith('.pptx'):
            presentation = Presentation(file_path)
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        all_text += shape.text        
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                all_text = file.read()

        if not all_text.strip():
            print("Failed to extract text from the document.")
            flash("Failed to extract text from the document.")
            continue

        splitted_text = split_documents(all_text)
        for text in splitted_text:

            document_obj = ChatDocument(
                page_content= text,
                metadata = {
                        "id": str(uuid4()),
                        "title": document.title,
                        "file_path": file_path,
                        "document_id": document.id,                        
                    }
            )
            
            if len(vector_store_ids) == 0:
                print("Vector store is empty")
                vector_store = Chroma.from_documents(
                    embedding=embeddings,
                    collection_name="SPIL",
                    documents=[document_obj], 
                    persist_directory="vector_store",
                    ids=[document_obj.metadata['id']])
                print("Vector store created")
            else:
                print("Vector store is not empty")
                vector_store.add_documents(
                    documents=[document_obj], 
                    ids=[document_obj.metadata['id']]
                )
                print("Document with ID", document.id, "added to vector store")

    for metadata in vector_metadatas:
        if metadata['document_id'] not in document_ids:
            vector_store.delete(ids=[metadata['id']])
            print(f"Deleted vector with id {metadata['id']}")

    flash('Vector database reloaded successfully!')
    return redirect(url_for('guide_bot.manage_documents'))