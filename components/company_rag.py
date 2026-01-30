import os
import sqlite3
from pathlib import Path
import streamlit as st
from urllib import response
from dotenv import load_dotenv
import json
from datetime import datetime

# LangChain Imports
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

class CompanyKnowledgeBase:
    """
    The Brain of Dataquartz: 
    Manages document indexing, semantic routing, and personalized AI responses.
    """
    def __init__(self):
        # 1. Configuration Setup
        load_dotenv() 
        
        # Priority: st.secrets (Cloud) -> os.getenv (.env file)
        self.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            st.error("🔑 API Key Missing! Set 'OPENAI_API_KEY' in Streamlit Secrets.")
            st.stop()
        
        # 2. Path Definitions
        self.kb_path = Path("knowledge_base")
        self.db_path = Path("vector_stores/db_faiss")
        self.manifest_path = self.db_path.parent / "kb_manifest.json"
        
        # 3. AI Models
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=self.api_key)
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0, 
            api_key=self.api_key,
            max_tokens=500
        )

    def _get_personality(self):
        """DATABASE LOOKUP: Fetches the custom tone set by the Admin."""
        try:
            conn = sqlite3.connect("dataquartz.db")
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'personality'")
            res = cursor.fetchone()
            conn.close()
            return res[0] if res else "Professional and concise"
        except Exception:
            return "Professional and concise"

    def _get_kb_map(self):
        """Reads the 'Semantic Map' for the Smart Router."""
        if not self.manifest_path.exists():
            return "General company knowledge base."
        with open(self.manifest_path, "r") as f:
            return json.load(f).get("summary", "")

    def update_manifest(self):
        """DETAILED CATALOGING: Creates an indexed list of topics found in the KB."""
        if not self.db_path.exists(): 
            return
        
        vectorstore = FAISS.load_local(
            str(self.db_path), self.embeddings, allow_dangerous_deserialization=True
        )
        
        # Sample k=6 for a broader view of company topics
        samples = vectorstore.similarity_search("List all different topics and services", k=6)
        combined_text = "\n".join([s.page_content[:600] for s in samples])
        
        prompt = f"""
        Analyze these snippets from a company's private documents:
        {combined_text}
        
        Create a 'Knowledge Map' for an AI Router. 
        List every unique topic found. For each topic, provide a 1-sentence description.
        Format:
        - [Topic Name]: [What it covers]
        
        If the snippets cover multiple unrelated areas, list them all clearly.
        """
        summary = self.llm.invoke(prompt).content
        
        with open(self.manifest_path, "w") as f:
            json.dump({"summary": summary, "updated": str(datetime.now())}, f)

    def index_documents(self):
        """Processes raw PDFs and builds the searchable Vector Database."""
        try:
            if not self.kb_path.exists():
                self.kb_path.mkdir(parents=True)
                return False

            loader = DirectoryLoader(str(self.kb_path), glob="./*.pdf", loader_cls=PyPDFLoader)
            documents = loader.load()

            if not documents: return False

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            split_docs = text_splitter.split_documents(documents)

            vectorstore = FAISS.from_documents(split_docs, self.embeddings)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(str(self.db_path))
            return True
        except Exception as e:
            print(f"Indexing Error: {e}")
            return False


def query(self, user_question, extra_context="", history=[]):
    """
    THE DATAQUARTZ BRAIN:
    1. Loads persona from the prompt folder.
    2. Routes queries based on KB relevance.
    3. Injects data into a strict system prompt.
    """
    
    # --- STEP 1: IMPORT SYSTEM PERSONA ---
    # Logic: Read the text file from your 'prompt' folder
    try:
        with open("prompts/persona.txt", "r") as f:
            persona_template = f.read()
    except FileNotFoundError:
        # Fallback if the file is missing during deployment
        persona_template = "You are the Dataquartz Assistant. Answer based on context: {context}\nQuestion: {user_question}"

    # --- STEP 2: FORMAT CHAT HISTORY ---
    formatted_history = ""
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted_history += f"{role}: {msg['content']}\n"

    # --- STEP 3: IDENTITY-AWARE ROUTING ---
    kb_map = self._get_kb_map()
    router_prompt = f"""
    KB Map: {kb_map}
    User Question: {user_question}
    Does this ask about Dataquartz or specific business data? (You/Your = Dataquartz).
    Answer ONLY YES or NO.
    """
    decision_resp = self.llm.invoke(router_prompt).content.strip().upper()

    # --- STEP 4: DYNAMIC RETRIEVAL ---
    context = ""
    docs = []
    if "YES" in decision_resp and self.db_path.exists():
        vectorstore = FAISS.load_local(
            str(self.db_path), self.embeddings, allow_dangerous_deserialization=True
        )
        # We use a 0.4 threshold as per your current settings
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 4, "score_threshold": 0.4}
        )
        docs = retriever.invoke(user_question)
        
        if not docs:
            docs = vectorstore.similarity_search(user_question, k=2)
            
        context = "\n\n---\n\n".join([d.page_content for d in docs])

    # --- STEP 5: FILL THE PERSONA & GENERATE ---
    # Logic: .format() fills the {placeholders} we put in persona.txt
    personality_tone = self._get_personality()
    
    final_prompt = persona_template.format(
        personality_tone=personality_tone,
        formatted_history=formatted_history if formatted_history else "New chat started.",
        context=context if context else "No company records found for this query.",
        extra_context=extra_context if extra_context else "No new files uploaded.",
        user_question=user_question
    )

    response = self.llm.invoke(final_prompt)
    
    return {
        "answer": response.content,
        "sources": [d.metadata.get('source', 'Knowledge Base') for d in docs],
        "used_kb": "YES" in decision_resp or len(extra_context) > 0
    }
