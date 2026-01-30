import os
from dotenv import load_dotenv

from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings


load_dotenv()


DB_CONNECTION = os.getenv("PG_CONN")
COLLECTION_NAME = "documents"
DOCUMENT_PATH = "knowledge_base.txt"

# -------------------------
# Load document
# -------------------------
with open(DOCUMENT_PATH, "r", encoding="utf-8") as f:
    raw_text = f.read()
   

# -------------------------
# Chunking
# -------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80
)

chunks = text_splitter.split_text(raw_text)

print(f"Total chunks created: {len(chunks)}")

# -------------------------
# Embeddings
# -------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# -------------------------
# Store in pgvector
# -------------------------
vectorstore = PGVector(
    embeddings,
    connection=DB_CONNECTION,
    collection_name=COLLECTION_NAME,
    pre_delete_collection=True  # clears old data
)

vectorstore.add_texts(chunks)

print("Ingestion completed successfully.")