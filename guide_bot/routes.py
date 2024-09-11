# guide_bot/routes.py
import io
import re
from uuid import uuid4
from flask import Blueprint, abort, render_template, redirect, send_file, send_from_directory, url_for, flash, request, session
from langchain_chroma import Chroma
import markdown
from app.auth import otp_required
from guide_bot.models import Document
from guide_bot.forms import DocumentFileForm, DocumentFolderForm, NewFolderForm, EditFileForm
from app import db

from langchain_huggingface import HuggingFaceEmbeddings
import os
from langchain_core.documents import Document as ChatDocument
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from guide_bot import conversation_chat, create_conversational_chain, load_vector_store, save_uploaded_file, load_saved_files, split_documents, extract_text_from_file, embeddings

guide_bot = Blueprint('guide_bot', __name__)

GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\t\n]', '_', filename)

# Don't forget to update the manage_documents route to save documents with their ids
# @guide_bot.route('/guide-bot/documents', methods=['GET', 'POST'])
# @login_required
# def manage_documents():
#     file_form = DocumentFileForm()
#     folder_form = DocumentFolderForm()
    
#     # Ambil page dan items_per_page dari parameter query, default page=1 dan per_page=10
#     page = request.args.get('page', 1, type=int)
#     items_per_page = request.args.get('items_per_page', 10, type=int)
    
#     # Ambil query pencarian dari parameter query
#     search_query = request.args.get('search_query', '', type=str)

#     # Get the current user's role
#     user_role = current_user.role
    
#     # Filter dokumen berdasarkan search query jika ada
#     if search_query:
#         documents = Document.query.filter(Document.title.ilike(f'%{search_query}%')).paginate(page=page, per_page=items_per_page)
#     else:
#         documents = Document.query.paginate(page=page, per_page=items_per_page)
    
#     # Proses penambahan dokumen
#     if file_form.validate_on_submit() or folder_form.validate_on_submit():
#         files = request.files.getlist('files')
#         allowed_roles = ','.join(file_form.allowed_roles.data)
#         for file in files:
#             filename = secure_filename(file.filename)
#             new_document = Document(title=filename, file=file.read(), allowed_roles=allowed_roles)
#             db.session.add(new_document)
#             db.session.commit()

#             # Save the file to disk with its document ID
#             save_dir = 'data'
#             if not os.path.exists(save_dir):
#                 os.makedirs(save_dir)
#             file_path = os.path.join(save_dir, f"{filename}")
#             with open(file_path, 'wb') as f:
#                 f.write(new_document.file)

#         flash('Document added successfully!')
#         return redirect(url_for('guide_bot.manage_documents', page=page, items_per_page=items_per_page, search_query=search_query))

#     # Proses penambahan dokumen
#     if folder_form.validate_on_submit():
#         files = request.files.getlist('files')
#         allowed_roles = ','.join(folder_form.allowed_roles.data)  # Handle roles similarly for folder form
#         for file in files:
#             filename = secure_filename(file.filename)
#             # Simpan dokumen dalam database
#             new_document = Document(title=filename, file=file.read(), allowed_roles=allowed_roles)
#             db.session.add(new_document)
#             db.session.commit()

#             # Save the file to disk with its document ID
#             save_dir = 'data'
#             if not os.path.exists(save_dir):
#                 os.makedirs(save_dir)
#             file_path = os.path.join(save_dir, f"{filename}")
#             with open(file_path, 'wb') as f:
#                 f.write(new_document.file)

#         # flash('Document added successfully!')
#         # return redirect(url_for('guide_bot.manage_documents', page=page, items_per_page=items_per_page, search_query=search_query))
    
#     # Render halaman dengan form dan dokumen terpaginate
#     return render_template('guide_bot/manage_documents.html', 
#                            file_form=file_form, 
#                            folder_form=folder_form, 
#                            documents=documents, 
#                            items_per_page=items_per_page, 
#                            search_query=search_query,
#                            user_role=user_role)

UPLOAD_FOLDER = 'uploads'

def save_file(current_dir, file, allowed_roles=None):
    """Menyimpan file ke subdirektori yang sesuai"""
    subdir = '/'.join(file.filename.split('/')[:-1])
    filename = file.filename.split('/')[-1]
    dirpath = os.path.join(current_dir, subdir)        
    
    # Buat subdirektori jika belum ada
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)    
    
    # Simpan file ke direktori
    filepath = os.path.join(dirpath, filename)
    file.save(filepath)
    # Simpan ke database
    new_document = Document(
        title=filename, 
        file=file.read(),
        dir=filepath, 
        allowed_roles=allowed_roles)
    db.session.add(new_document)
    db.session.commit()

def get_file_structure_db(current_dir, document_dirs):
    """Membuat struktur file dari document_dirs di dalam current_dir"""
    file_structure = {}
    dirs = []
    files = []
    print('ROOT: ', '/'.join(current_dir.split('/')[1:]))
    for dir in document_dirs:
        if '/'.join(dir.split('/')[:-1]) == '/'.join(current_dir.split('/')[1:]):        
            files.append(dir.split('/')[-1])
        elif len(dir.split('/')) > 0 and dir.split('/')[0] not in dirs:
            dirs.append(dir.split('/')[0])
        print('/'.join(dir.split('/')[:-1]))

    file_structure[''] = {'dirs': dirs, 'files': files}
    # print("File structure from DB:", file_structure)
    return file_structure

def get_file_structure(root_dir):
    """Membuat struktur file hanya di level direktori saat ini"""
    file_structure = {}
    
    # Hanya melihat isi dari direktori root tanpa masuk ke subfolder
    with os.scandir(root_dir) as entries:
        dirs = []
        files = []
        for entry in entries:
            if entry.is_dir():
                dirs.append(entry.name)
            elif entry.is_file():
                files.append(entry.name)
        file_structure[''] = {'dirs': dirs, 'files': files}
    # print("File structure:", file_structure)
    return file_structure

def get_next_folder(current_dir, document_dirs):
    # Set to hold unique folder names from the paths
    next_folders = set()
    
    # Iterate over all document directories
    for doc_dir in document_dirs:
        print("Comparing:", doc_dir, current_dir)
        # Check if the path starts with the current directory
        if doc_dir.startswith(current_dir):
            print("Found:", doc_dir)
            # Get the relative path after the current directory
            relative_path = doc_dir[len(current_dir):].strip('/')
            print("Relative path:", relative_path)
            # Split the relative path into parts
            path_parts = relative_path.split('/')
            print("Path parts:", path_parts)
            # If there's at least one part, the first part is the next folder
            if len(path_parts) > 1:
                next_folders.add(path_parts[0])

    # Return next folders as sorted list
    return sorted(next_folders)

def create_folder(current_dir, folder_name):
    """Membuat folder baru di direktori yang sesuai"""
    dirpath = os.path.join(current_dir, folder_name)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    
    index_path = os.path.join(dirpath, 'index')

    new_document = Document(
        title="index",
        dir=index_path,
        file=None,  
        allowed_roles=None)
    db.session.add(new_document)
    db.session.commit()

@guide_bot.route('/guide-bot/documents/', methods=['GET', 'POST'])
@guide_bot.route('/guide-bot/documents/<path:subdir>', methods=['GET', 'POST'])
@login_required
def manage_documents(subdir=''):
    current_dir = os.path.join(UPLOAD_FOLDER, subdir)
    file_form = DocumentFileForm()
    folder_form = DocumentFolderForm()
    new_folder_form = NewFolderForm()
    
    # Ambil query pencarian dari parameter query
    search_query = request.args.get('search_query', '', type=str)

    # Get the current user's role
    user_role = current_user.role
    
    # Filter dokumen berdasarkan search query jika ada
    if search_query:
        documents = Document.query.filter(Document.dir.ilike(f'%{search_query}%'))
        return render_template('guide_bot/manage_documents.html',                                
                               documents=documents,     
                               search_query=search_query,
                               user_role=user_role,
                               subdir=subdir)
    else:
        documents = Document.query.all()
    
    # Proses penambahan dokumen
    if file_form.validate_on_submit() or folder_form.validate_on_submit():
        if file_form.validate_on_submit():
            form = file_form
        elif folder_form.validate_on_submit():
            form = folder_form
        files = request.files.getlist('files')
        allowed_roles = ','.join(form.allowed_roles.data)
        for file in files:            
            save_file(current_dir, file, allowed_roles)
        
        flash('Document added successfully!')
        return redirect(url_for('guide_bot.manage_documents', subdir=subdir, search_query=search_query))    
    
    # Proses penambahan folder
    if new_folder_form.validate_on_submit():
        folder_name = new_folder_form.folder_name.data
        create_folder(current_dir, folder_name)
        flash('Folder created successfully!')
        return redirect(url_for('guide_bot.manage_documents', subdir=subdir, search_query=search_query))
    
    # file_structure = get_file_structure(current_dir)
    # print("File structure:", file_structure)
    # print("Current dir:", [dir for dir in current_dir.split('/') if dir != ''])
    folders = get_next_folder(current_dir, [document.dir for document in documents])
    documents = [document for document in documents if document.dir.split('/')[:-1] == [dir for dir in current_dir.split('/') if dir != '']]        
    # print("Folders:", folders)
    # Render halaman dengan form dan dokumen terpaginate
    active_dir = enumerate(subdir.split('/'))
    return render_template('guide_bot/manage_documents.html', 
                           file_form=file_form, 
                           folder_form=folder_form, 
                           new_folder_form=new_folder_form,
                           documents=documents, 
                           folders=folders,
                           search_query=search_query,
                           user_role=user_role,
                           subdir=subdir,
                           active_dir=active_dir)

@guide_bot.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@guide_bot.route('/guide-bot/documents/edit/<int:id>', methods=['POST'])
@login_required
def edit_document(id):
    document = Document.query.get_or_404(id)
    new_name = request.get_json().get('new_name')
    
    if new_name:        
        document.title = new_name        
        document.dir = os.path.join('/'.join(document.dir.split('/')[:-1]), new_name)
        db.session.commit()
        flash('Document updated successfully!')
        return redirect(url_for('guide_bot.manage_documents', subdir=""))
    
    return redirect(url_for('guide_bot.manage_documents', subdir=""))

@guide_bot.route('/guide-bot/documents/delete-multiple', methods=['POST'])
@login_required
def delete_multiple_documents():
    document_ids = request.form.getlist('document_ids')  # Use getlist to handle multiple values

    if not document_ids:
        flash('No documents selected for deletion.', 'warning')
        return redirect(url_for('guide_bot.manage_documents'))
    
    if not current_user.is_manager():
        flash('You do not have permission to delete documents.', 'error')
        return redirect(url_for('guide_bot.manage_documents'))

    deleted_files = []
    not_found_files = []
    errors = []

    for doc_id in document_ids:
        if doc_id:  # Ensure id is not empty
            document = Document.query.get(doc_id)
            if document:
                db.session.delete(document)
                file_path = document.dir
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                    except Exception as e:
                        errors.append(f'Error removing file {file_path}: {e}')
                else:
                    not_found_files.append(file_path)
            else:
                flash(f'Document with ID {doc_id} not found.', 'warning')
    
    db.session.commit()

    if deleted_files:
        flash(f'Selected documents deleted successfully: {", ".join(deleted_files)}', 'success')
    if not_found_files:
        flash(f'Files not found: {", ".join(not_found_files)}', 'warning')
    if errors:
        flash(f'Errors occurred: {", ".join(errors)}', 'error')

    return redirect(url_for('guide_bot.manage_documents'))

@guide_bot.route('/guide-bot/documents/delete/<int:id>', methods=['POST'])
def delete_document(id):
    document = Document.query.get_or_404(id)
    
    # Delete the document from the database
    db.session.delete(document)
    db.session.commit()

    # delete the file from the server
    # file_path = os.path.join('data', secure_filename(document.title))
    file_path = document.dir
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Successfully deleted file: {file_path}")  # Debugging statement
        except Exception as e:
            print(f"Error removing file {file_path}: {e}")
    else:
        print(f"File not found: {file_path}")

    flash('Document deleted successfully!')
    return redirect(url_for('guide_bot.manage_documents', subdir=""))

@guide_bot.route('/guide-bot/documents/view/<int:id>')
@login_required
def view_document(id):
    document = Document.query.get_or_404(id)
    return render_template('guide_bot/view_document.html', document=document)
    # if current_user.is_manager() or document.is_accessible_by(current_user):
    #     return render_template('guide_bot/view_document.html', document=document)
    # else:
    #     flash('You do not have permission to view this document.', 'error')
    #     return redirect(url_for('guide_bot.manage_documents'))

@guide_bot.route('/guide-bot/document/file/<int:document_id>')
def get_document_file(document_id):
    document = Document.query.get_or_404(document_id)
    if document.file:
        # Set appropriate MIME type based on file type
        return send_file(io.BytesIO(document.file), mimetype='application/pdf', as_attachment=False)
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

@guide_bot.route('/aios/guide-bot/chat', methods=['GET', 'POST'])
@otp_required
def chat():
    # Clear OTP data from session after successful login
    session.pop('otp', None)
    session.pop('otp_expiry', None)
    session.pop('otp_email', None)
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
            print("Source documents:", source_documents)
            print("Conversation completed"  )
            past.append(user_input)
            generated.append({
                "message": markdown.markdown(output),
                "source_documents": source_documents
            })
        else:
            flash('⚠️ No documents uploaded by admin yet.', 'warning')

    return render_template('guide_bot/index.html', past=past, generated=generated)

@guide_bot.route('/guide-bot/reload-vector-db', methods=['GET'])    
def reload_vector_db():
    vector_store = Chroma(
        collection_name=f"SPIL-{current_user.role}",
        embedding_function=embeddings or HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'}), 
        persist_directory=f"vector_store/{current_user.role}"
    )
    # Load all documents from the SQL database
    documents = Document.query.filter(Document.allowed_roles.ilike(f'%{current_user.role}%')).all()
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

        # Check if document.file is not None
        if document.file is None:
            print(f"Document {document.id} has no file.")
            flash(f"Document {document.id} has no file.")
            continue

        #  Save         
        file_path = os.path.join('data', secure_filename(document.title))
        with open(document.dir, 'wb') as f:
            f.write(document.file)
        
        # Extract text based on file type
        all_text = extract_text_from_file(file_path)

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
                    collection_name=f"SPIL-{current_user.role}",
                    documents=[document_obj], 
                    persist_directory=f"vector_store/{current_user.role}",
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