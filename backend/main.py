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
    model="policybot",
    temperature=0.2
)

# -------------------------
# Prompt (STRICT)
# -------------------------
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""
        Use the following context to answer the user question.

        Context:
        {context}

        User Question:
        {question}

        Answer:
    """
)


def map_confidence(avg_score: float):
    print(avg_score)
    if avg_score > 0.65:
        return "High"
    elif avg_score > 0.50:
        return "Medium"
    else:
        return "Low"


def generate_followups(context: str):
    """
    Extracts high-level IT policy explanation categories from document chunks. 
    Identifies which policy areas are relevant based on keywords in the provided text.

    Args:
        chunks (list[str]): List of text chunks retrieved as relevant context.

    Returns:
        list[str]: Unique list of human-readable policy explanation labels.
    """
    followups = set()
    t = context.lower()

    # Identity & Access
    if any(k in t for k in ["password", "authentication", "mfa", "identity"]):
        followups.update([
            "How do I reset my password?",
            "What are the password security requirements?",
            "Is multi-factor authentication mandatory?"
        ])

    # Privileged access
    if any(k in t for k in ["privileged", "admin", "elevated access"]):
        followups.update([
            "Are admin accounts subject to additional controls?",
            "Who approves privileged access?"
        ])

    # Software
    if any(k in t for k in ["software", "application", "license", "installation"]):
        followups.update([
            "How do I request new software?",
            "Can I install software without IT approval?",
            "What happens if unlicensed software is installed?"
        ])

    # Hardware & devices
    if any(k in t for k in ["hardware", "device", "laptop", "endpoint"]):
        followups.update([
            "Can I use my personal device for work?",
            "How are company devices managed?",
            "What should I do if my laptop is lost?"
        ])

    # Network & VPN
    if any(k in t for k in ["vpn", "network", "wi-fi", "remote access"]):
        followups.update([
            "How do I access VPN?",
            "Can I bypass VPN on trusted networks?",
            "Who do I contact for network issues?"
        ])

    # Security & incidents
    if any(k in t for k in ["security", "incident", "breach", "malware"]):
        followups.update([
            "How do I report a security incident?",
            "What happens after an incident is reported?",
            "How are incidents prioritized?"
        ])

    # Data protection
    if any(k in t for k in ["data", "encryption", "classification", "storage"]):
        followups.update([
            "How is company data classified?",
            "Where can sensitive data be stored?",
            "Is encryption required for all data?"
        ])

    # Onboarding / Offboarding
    if any(k in t for k in ["onboarding", "offboarding", "termination", "resignation"]):
        followups.update([
            "What happens to system access when an employee leaves?",
            "How is access revoked after resignation?"
        ])

    # Fallback (first-time / generic)
    if not followups:
        followups.update([
            "What services does the IT Helpdesk provide?",
            "How can I contact IT support?",
            "What issues are not supported by IT?"
        ])

    return list(followups)[:3]



def extract_explanations(chunks: list[str]):
    explanations = set()

    for text in chunks:
        t = text.lower()

        # Identity & Access
        if any(k in t for k in ["password", "authentication", "mfa", "identity"]):
            explanations.add("IT Policy → Identity & Access Management")

        # Privileged access
        if any(k in t for k in ["privileged", "admin", "elevated access"]):
            explanations.add("IT Policy → Privileged Access Control")

        # Software
        if any(k in t for k in ["software", "application", "license", "installation"]):
            explanations.add("IT Policy → Software Installation & Licensing")

        # Hardware & devices
        if any(k in t for k in ["hardware", "device", "laptop", "endpoint"]):
            explanations.add("IT Policy → Hardware & Device Management")

        # Network & VPN
        if any(k in t for k in ["vpn", "network", "wi-fi", "remote access"]):
            explanations.add("IT Policy → Network & Remote Access")

        # Email & collaboration
        if any(k in t for k in ["email", "messaging", "collaboration"]):
            explanations.add("IT Policy → Email & Collaboration Tools")

        # Data protection
        if any(k in t for k in ["data", "encryption", "classification", "storage"]):
            explanations.add("IT Policy → Data Protection & Handling")

        # Security & incidents
        if any(k in t for k in ["security", "incident", "breach", "malware"]):
            explanations.add("IT Policy → Security & Incident Management")

        # Change & operations
        if any(k in t for k in ["change management", "patch", "maintenance"]):
            explanations.add("IT Policy → Change & Operations Management")

        # Compliance & audit
        if any(k in t for k in ["audit", "compliance", "monitoring", "logging"]):
            explanations.add("IT Policy → Compliance & Audit")

        # Acceptable use
        if any(k in t for k in ["acceptable use", "personal use", "misuse"]):
            explanations.add("IT Policy → Acceptable Use")

        # Onboarding / Offboarding
        if any(k in t for k in ["onboarding", "offboarding", "termination", "resignation"]):
            explanations.add("IT Policy → User Lifecycle Management")

        # Exceptions & enforcement
        if any(k in t for k in ["exception", "violation", "disciplinary", "enforcement"]):
            explanations.add("IT Policy → Policy Enforcement & Exceptions")

    return list(explanations)




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
        filtered = [(doc, score) for doc, score in results if score > SIMILARITY_THRESHOLD]

        if not filtered:
            return {"response": "I can only help with IT Helpdesk related questions."}

        avg_score = sum(score for _, score in filtered) / len(filtered)
        confidence = map_confidence(avg_score)

        relevant_docs = [doc.page_content for doc, _ in filtered]

        
        print(relevant_docs)

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
        # return {"response": response["messages"][-1].content}
        answer_text = response["messages"][-1].content
        followups = generate_followups(context)
        
        explanations = extract_explanations(relevant_docs)

        
        return {
            "response": answer_text,
            "followups": followups,
            "confidence": confidence,
            "confidence_score": round(avg_score, 3),
            "explanations": explanations
        }


    except Exception as e:
        return {"response": f"Error processing your request: {str(e)}"}

