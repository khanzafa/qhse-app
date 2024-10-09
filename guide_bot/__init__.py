import os
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

# Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'})

# Extracting text from uploaded file
def extract_text_from_file(file_path):    
    elements = partition(filename=file_path)
    return "\n\n".join([str(el) for el in elements])

# Function to handle conversation with the chatbot
def conversation_chat(query, chain, history):
    result = chain.invoke({"question": query, "chat_history": history})
    answer = result["answer"]        
    history.append((query, answer))
    # Assuming result contains relevant document metadata, such as filenames
    if "source_documents" in result and result["source_documents"]:                    
        return history, answer, result["source_documents"]
    
    return history, answer, None

# Function to create the conversational chain
def create_conversational_chain(vector_store):
    prompt_template = ChatPromptTemplate([
        ("system", "Anda adalah AI Bot yang sangat membantu di lingkungan PT. Salam Pacific Indonesia Lines. Nama Anda adalah GuideBot."),
        ("human", 
         """
            Jika input bukan pertanyaan atau konteks tidak tersedia, jawab dengan informasi yang relevan berdasarkan pemahaman umum Anda.
            Jika input adalah pertanyaan, berikan jawaban yang jelas dan akurat dalam bahasa Indonesia.
            Jika ada informasi dalam konteks, gunakan konteks tersebut untuk memberikan jawaban yang akurat.
            Jika tidak ada konteks atau jawaban yang tepat, katakan 'Maaf, saya tidak tahu jawabannya'.
            
            Pertanyaan: {question}
            Konteks yang tersedia: {context}
            Jawaban:
         """)
    ])

    # LLAMA GROQ
    llm = ChatGroq(
        groq_api_key=os.getenv('GROQ_API_KEY'), 
        model_name='llama3-70b-8192'
    )

    # if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    #     os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")

    # endpoint = HuggingFaceEndpoint(
    #     repo_id="bigscience/bloom",
    #     task="text-generation",
    #     max_new_tokens=4096,
    #     do_sample=False,
    #     repetition_penalty=1.03,
    # )

    # # LLAMA HUGGING FACE
    # llm = ChatHuggingFace(llm=endpoint)    

    # GEMINI
    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-1.5-flash",
    #     temperature=0,
    #     max_tokens=None,
    #     timeout=None,
    #     max_retries=2,
    # )

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')

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
    
    return chain

def load_vector_store(embeddings):
    vector_store = Chroma(
        collection_name=f"SPIL",
        embedding_function=embeddings or HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={'device': 'cpu'}), 
        persist_directory=f"vector_store"
    )
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