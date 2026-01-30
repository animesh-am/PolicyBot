import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_postgres import PGVector
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_agent

load_dotenv()

# -------------------------
# App
# -------------------------
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins="http://localhost:3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Config
# -------------------------
DB_CONNECTION = os.getenv("PG_CONN")
COLLECTION_NAME = "documents"
SIMILARITY_THRESHOLD = 0.25  # Adjust for stricter/looser responses

# -------------------------
# Embeddings
# -------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = PGVector(
    embeddings,
    connection=DB_CONNECTION,
    collection_name=COLLECTION_NAME,
)

# -------------------------
# LLM
# -------------------------
llm = ChatOllama(
    model="llama3.1:8b",
    temperature=0.2
)

# -------------------------
# Prompt (STRICT)
# -------------------------
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an internal IT helpdesk assistant. Answer ONLY using the provided context.
If the question is unrelated, respond: "I can only help with IT helpdesk related questions."
For greetings, respond politely. Do not guess or fabricate information.
Context: {context}
User Question: {question}
Answer: """
)

# -------------------------
# Request Model
# -------------------------
class ChatRequest(BaseModel):
    message: str

# -------------------------
# Chat Endpoint
# -------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    user_input = req.message.strip().lower()

    # ---- Greeting short-circuit
    if user_input in {"hi", "hello", "hey", "good morning", "good evening"}:
        return {"response": "Hello! How can I assist you with IT Helpdesk related queries?"}

    try:
        # ---- Similarity search WITH scores
        results = vectorstore.similarity_search_with_score(
            req.message,
            k=3
        )

        # ---- Hard rejection if nothing relevant
        if not results:
            return {"response": "I can only help with IT Helpdesk related questions."}

        # ---- Score filtering
        relevant_docs = [
            doc.page_content
            for doc, score in results
            if score > SIMILARITY_THRESHOLD
        ]

        if not relevant_docs:
            return {"response": "I can only help with IT Helpdesk related questions."}

        context = "\n\n".join(relevant_docs)

        final_prompt = prompt.format(
            context=context,
            question=req.message
        )

        # ---- Create and invoke agent
        agent = create_agent(
            model=llm,
            tools=[],
            system_prompt="You are an internal chatbot for the company. Please answer questions in natural language."
        )

        response = agent.invoke({
            "messages": [{"role": "user", "content": f"User Query: {final_prompt}"}]
        })

        # Return the message content
        return {"response": response["messages"][-1].content}

    except Exception as e:
        return {"response": f"Error processing your request: {str(e)}"}

