# guide_bot/routes.py
import io
import re
from flask import Blueprint, abort, render_template, redirect, send_file, url_for, flash, request, session
from langchain_chroma import Chroma
from guide_bot.models import Document
from guide_bot.forms import DocumentForm
from app import db
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
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


guide_bot = Blueprint('guide_bot', __name__)

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\t\n]', '_', filename)

from werkzeug.utils import secure_filename

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


        # # Extract text based on file type
        # all_text = ""
        # if file_path.endswith('.pdf'):
        #     pdf_reader = PdfReader(file_path)
        #     for page in pdf_reader.pages:
        #         text = page.extract_text()
        #         if text:
        #             all_text += text
        # elif file_path.endswith('.docx'):
        #     all_text = docx2txt.process(file_path)
        # elif file_path.endswith('.txt'):
        #     with open(file_path, 'r', encoding='utf-8') as file:
        #         all_text = file.read()
        
        # new_document_obj = ChatDocument(
        #      page_content= all_text,
        #      metadata = {
        #             "title": form.title.data,
        #             "file_path": file_path
        #         }
        #  )

        # # Ensure text is not empty
        # if not all_text.strip():
        #     print("Failed to extract text from the document.")
        #     flash("Failed to extract text from the document.")

        # # Split the document text into chunks
        # text_chunks = split_documents(all_text)

        # if text_chunks:
        #     embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        #     vector_store = load_vector_store(embeddings)

        #     if vector_store is None:
        #         # vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
        #         vector_store = FAISS.from_documents([new_document_obj], embedding=embeddings)
        #     else:
        #         # vector_store.add_texts(text_chunks, ids=[str(new_document.id)])  # Use document ID as the vector ID
        #         vector_store.add_documents(new_document_obj, ids=[str(new_document.id)])  # Use document ID as the vector ID

        #     # Save the updated vector store
        #     save_vector_store(vector_store)
        # else:
        #     flash("No valid text extracted from the document.")

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
    
    # # Load the vector store
    # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    # vector_store = load_vector_store(embeddings)
    
    # # Remove the vector corresponding to the document from FAISS
    # if vector_store:
    #     # Assuming document.title is unique and was used as an identifier
    #     vector_store.delete(ids=[str(id)])
    #     save_vector_store(vector_store)
    
    # Delete the document from the database
    db.session.delete(document)
    db.session.commit()

    # delete the file from the server
    file_path = os.path.join('data', sanitize_filename(document.title))
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

# # Function to handle conversation with the chatbot
# def conversation_chat(query, chain, history):
#     result = chain({"question": query, "chat_history": history})
#     history.append((query, result["answer"]))
#     return result["answer"]

# Function to handle conversation with the chatbot
def conversation_chat(query, chain, history):
    result = chain.invoke({"question": query, "chat_history": history})
    answer = result["answer"]        
    history.append((query, answer))
    # Assuming result contains relevant document metadata, such as filenames
    if "source_documents" in result and result["source_documents"]:                    
        return answer, result["source_documents"]
    
    return answer, []

# Function to create the conversational chain
def create_conversational_chain(vector_store):
    # prompt_template = ChatPromptTemplate.from_template("""
    #     Tolong jawab pertanyaan berikut dalam bahasa Indonesia.
    #     Perkenalkan dirimu sebagai 'GuideBot', asisten virtual yang siap membantu.
    #     Jika informasi dalam konteks tersedia, gunakan untuk memberikan jawaban yang akurat, jelas, dan to the point. 
    #     Jika tidak ada konteks atau jawaban yang tepat, katakan 'Maaf, saya tidak tahu jawabannya'.
    #     Pertanyaan: {question}
    #     Konteks: {context}
    #     Jawaban:
    # """)

    prompt_template = ChatPromptTemplate([
        ("system", "Anda adalah AI Bot yang sangat membantu di lingkungan PT. Salam Pacific Indonesia Lines. Nama Anda adalah GuideBot."),
        ("human", 
         """
            Tolong jawab pertanyaan berikut dalam bahasa Indonesia.
            Jika informasi dalam konteks tersedia, gunakan untuk memberikan jawaban yang akurat dan jelas.
            Jika tidak ada konteks atau jawaban yang tepat, katakan 'Maaf, saya tidak tahu jawabannya'.
            Pertanyaan: {question}
            Konteks: {context}
            Jawaban:
         """)
    ])

    llm = ChatGroq(
        groq_api_key=os.getenv('GROQ_API_KEY'), 
        model_name='llama3-70b-8192'
    )

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        chain_type='stuff',
        retriever=vector_store.as_retriever(search_kwargs={"k": 1}),
        return_source_documents=True,
        memory=memory,
        combine_docs_chain_kwargs={
            "prompt": prompt_template,
            "document_variable_name": "context" 
        },
        
    )    
    
    return chain

# Function to save uploaded file to the server
def save_uploaded_file(uploaded_file):
    save_dir = 'data'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    file_path = os.path.join(save_dir, uploaded_file.filename)
    uploaded_file.save(file_path)
    return file_path

# Function to load all saved files from the server
def load_saved_files():
    save_dir = 'data'
    if not os.path.exists(save_dir):
        return []
    return [os.path.join(save_dir, f) for f in os.listdir(save_dir)]

# Function to split documents into smaller chunks
def split_documents(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_text(text)

# Function to save the vector store to disk
def save_vector_store(vector_store, save_dir="faiss_index_dir"):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    index_path = os.path.join(save_dir, "faiss_index.index")
    vector_store.save_local(index_path)

# Function to load the vector store from disk
# def load_vector_store(embeddings, save_dir="faiss_index_dir"):
#     index_path = os.path.join(save_dir, "faiss_index.index")
#     if os.path.exists(index_path):
#         vector_store = FAISS.load_local(
#             index_path, embeddings, allow_dangerous_deserialization=True
#         )   
#         return vector_store
#     return None

def load_vector_store(embeddings):
    vector_store = Chroma(
        collection_name="SPIL",
        embedding_function=embeddings or HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'}), 
        persist_directory="vector_store"
    )
    return vector_store

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
            output, source_documents = conversation_chat(user_input, chain, history)
            print("Conversation completed")
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
        # elif file_path.endswith('.doc'):
        #     pythoncom.CoInitialize()
        #     try:
        #         word = win32com.client.Dispatch("Word.Application")
        #         print("File path:", file_path)
        #         doc = word.Documents.Open(file_path)
        #         for paragraph in doc.Paragraphs:
        #             all_text += paragraph.Range.Text
        #         doc.Close()
        #         word.Quit()
        #     finally:
        #         pythoncom.CoUninitialize()
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

        document_obj = ChatDocument(
             page_content= all_text,
             metadata = {
                    "title": document.title,
                    "file_path": file_path,
                    "id": document.id
                }
        )
        
        if len(vector_store_ids) == 0:
            print("Vector store is empty")
            vector_store = Chroma.from_documents(
                embedding=embeddings,
                collection_name="SPIL",
                documents=[document_obj], 
                persist_directory="vector_store",
                ids=[str(document.id)])
            print("Vector store created")
        else:
            print("Vector store is not empty")
            vector_store.add_documents(
                documents=[document_obj], 
                ids=[str(document.id)]
            )
            print("Document with ID", document.id, "added to vector store")

    for vector_id in vector_store_ids:
        if vector_id not in document_ids:
            vector_store.delete(ids=[vector_id])
            print(f"Deleted vector with id {vector_id}")

    flash('Vector database reloaded successfully!')
    return redirect(url_for('guide_bot.manage_documents'))