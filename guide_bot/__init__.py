import os
import logging
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace, HuggingFaceEmbeddings, HuggingFaceEndpoint, HuggingFacePipeline
from langchain_google_genai import ChatGoogleGenerativeAI
from unstructured.partition.auto import partition
from flask_login import current_user
from flask import session, current_app
import PIL
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'})
logging.info("Embeddings initialized.")

# Extracting text from uploaded file
def extract_text_from_file(file_path):    
    logging.info(f"Extracting text from file: {file_path}")
    elements = partition(filename=file_path)
    text = "\n\n".join([str(el) for el in elements])
    logging.info("Text extraction complete.")
    return text

# Function to handle conversation with the chatbot
def conversation_chat(query, chain, history):
    logging.info(f"Received query: {query}")
    result = chain.invoke({"question": query, "chat_history": history})
    answer = result["answer"]        
    history.append((query, answer))
    logging.info(f"Answer generated: {answer}")

    # Assuming result contains relevant document metadata, such as filenames
    if "source_documents" in result and result["source_documents"]:
        logging.info("Source documents retrieved.")
        return history, answer, result["source_documents"]
    
    logging.warning("No source documents found.")
    return history, answer, None

# Function to create the conversational chain
def create_conversational_chain(vector_store):
    prompt_template = ChatPromptTemplate([
        ("system", "Anda adalah AI Bot yang sangat membantu di lingkungan PT. Salam Pacific Indonesia Lines. Nama Anda adalah GuideBot."),
        ("human", 
         """
            Anda diharapkan untuk memberikan jawaban yang informatif dan relevan. Berikut adalah langkah-langkah yang harus Anda ikuti:
            
            1. **Identifikasi Jenis Input**:
                - Jika input bukan pertanyaan atau konteks tidak tersedia, gunakan pengetahuan umum Anda untuk memberikan informasi relevan.
                - Jika input adalah pertanyaan, lanjutkan ke langkah berikutnya.
            
            2. **Gunakan Konteks**:
                - Jika terdapat informasi dalam konteks, manfaatkan konteks tersebut untuk merespon pertanyaan.
                - Jika konteks tidak tersedia atau tidak relevan, Anda akan memberikan jawaban berdasarkan pengetahuan umum.
            
            3. **Tanggapan Akhir**:
                - Jika Anda memiliki jawaban yang tepat, berikan dengan jelas dan akurat dalam bahasa Indonesia.
                - Jika Anda tidak memiliki jawaban, katakan 'Maaf, saya tidak tahu jawabannya'.
            
            Pertanyaan: {question}
            Konteks yang tersedia: {context}
            Jawaban:
         """)
    ])

    logging.info("Creating conversational chain.")
    # LLAMA GROQ
    llm = ChatGroq(
        groq_api_key=os.getenv('GROQ_API_KEY'), 
        model_name='llama3-70b-8192'
    )

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')

    # Create the conversational retrieval chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        chain_type='stuff',
        retriever=vector_store.as_retriever(search_type="similarity_score_threshold", search_kwargs={"k": 1, 'score_threshold': 0.5}),
        return_source_documents=True,
        memory=memory,
        combine_docs_chain_kwargs={
            "prompt": prompt_template,
            "document_variable_name": "context" 
        },        
    )
    
    logging.info("Conversational chain created successfully.")
    return chain

def load_vector_store(embeddings):
    logging.info("Loading vector store.")
    vector_store = Chroma(
        collection_name="SPIL",
        embedding_function=embeddings or HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'}), 
        persist_directory="vector_store"
    )
    logging.info("Vector store loaded successfully.")
    return vector_store

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
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_text(text)