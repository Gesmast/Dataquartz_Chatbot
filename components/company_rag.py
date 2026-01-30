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
        """THE GATEKEEPER: Routes the query with history awareness and maintains memory."""
        
        # 1. Format Chat History (Maintain Memory)
        formatted_history = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted_history += f"{role}: {msg['content']}\n"
    
        # 2. History-Aware Routing Decision
        kb_map = self._get_kb_map()
        router_prompt = f"""
        You are the Traffic Controller for Dataquartz. 
        KB Map (Topics we have documents for): {kb_map}
        
        Recent Conversation:
        {formatted_history[-1000:] if formatted_history else "No previous history."}
        
        Current Question: {user_question}
        
        TASK: Based on the KB Map, does this question require searching our company documents?
        - Answer YES only if it relates to company data, rules, or the KB Map.
        - Answer NO for greetings, general knowledge (weather, time), or irrelevant topics.
        
        Answer only YES or NO.
        """
        decision_resp = self.llm.invoke(router_prompt).content.strip().upper()
    
        # 3. Retrieval Path (Dynamic Search)
        context = ""
        docs = []
        if "YES" in decision_resp and self.db_path.exists():
            vectorstore = FAISS.load_local(
                str(self.db_path), self.embeddings, allow_dangerous_deserialization=True
            )
            
            # Dynamic Retrieval with 50% relevance threshold
            retriever = vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"k": 5, "score_threshold": 0.5}
            )
            
            docs = retriever.invoke(user_question)
            
            # Fallback to standard search if threshold is too strict
            if not docs:
                docs = vectorstore.similarity_search(user_question, k=2)
    
            context = "\n\n---\n\n".join([d.page_content for d in docs])
    
        # 4. Fetch Custom Personality from DB
        personality_tone = self._get_personality()
    
        # 5. THE FINAL CONSOLIDATED PROMPT (Persona + Logic + Data)
        system_persona_prompt = f"""
        ### ROLE
        You are the "Dataquartz Intelligence Assistant." Your current tone is: {personality_tone}.
        You are professional, accurate, and strictly bound by the provided data.
    
        ### TASKS & DUTIES
        1. Provide answers based ONLY on the provided Context blocks below.
        2. KB FIRST: Always prioritize the Knowledge Base. 
        3. NO HALLUCINATION: If the information is not in the context, do not make it up.
    
        ### GUARDRAILS
        - IRRELEVANCE POLICY: If asked about topics outside of business or company data (e.g., weather, recipes), state that you only assist with Dataquartz data.
        - REDIRECTION: If the answer is missing, finish with: "For further assistance, please contact sales@dataquartz.com."
    
        ### EXECUTION STEPS
        1. Check [CONVERSATION HISTORY] for user details (like names).
        2. Check [TEMPORARY UPLOADED FILE CONTEXT] first—this is high priority for specific file questions.
        3. Check [PERMANENT COMPANY CONTEXT] for general company rules.
    
        [CONVERSATION HISTORY]
        {formatted_history if formatted_history else "No previous history."}
    
        [PERMANENT COMPANY CONTEXT]
        {context if context else "No company documents retrieved for this query."}
    
        [TEMPORARY UPLOADED FILE CONTEXT]
        {extra_context if extra_context else "No temporary files uploaded."}
    
        [USER QUESTION]
        {user_question}
        """
    
        response = self.llm.invoke(system_persona_prompt)
    
    return {
        "answer": response.content,
        "sources": [d.metadata.get('source', 'Unknown') for d in docs],
        "used_kb": "YES" in decision_resp or len(extra_context) > 0
    }
