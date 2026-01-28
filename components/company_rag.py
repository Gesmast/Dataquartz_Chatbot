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
        """
        DATABASE LOOKUP: Fetches the custom tone set by the Admin.
        This ensures the AI sounds like a peer, a professional, or a formal assistant.
        """
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
        """
        AUTO-SUMMARY: Reads the vector store and updates the manifest.
        This allows the Router to know what's in the KB without a full search.
        """
        if not self.db_path.exists(): return
        
        vectorstore = FAISS.load_local(
            str(self.db_path), self.embeddings, allow_dangerous_deserialization=True
        )
        # Sample content for the map
        samples = vectorstore.similarity_search("Topics summary", k=3)
        combined_text = "\n".join([s.page_content[:500] for s in samples])
        
        prompt = f"Summarize the core topics covered in these snippets for an AI router: {combined_text}"
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
        THE GATEKEEPER: Routes the query with history awareness and maintains memory.
        """
        # 1. Format Chat History for the LLM
        # This transforms the list of messages into a readable transcript
        formatted_history = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted_history += f"{role}: {msg['content']}\n"

        # 2. History-Aware Routing Decision
        # We include history here so the router knows what "it" or "that" refers to
        kb_map = self._get_kb_map()
        router_prompt = f"""
        KB Map: {kb_map}
        
        Recent Conversation:
        {formatted_history[-1000:] if formatted_history else "No previous history."}
        
        Current Question: {user_question}
        
        Based on the conversation and the KB Map, does the AI need to search the company PDFs to answer the current question? 
        Answer only YES or NO.
        """
        decision_resp = self.llm.invoke(router_prompt).content.strip().upper()

        # 3. Retrieval Path
        context = ""
        docs = []
        if "YES" in decision_resp and self.db_path.exists():
            vectorstore = FAISS.load_local(
                str(self.db_path), self.embeddings, allow_dangerous_deserialization=True
            )
            # Search the vector DB using the user's latest question
            docs = vectorstore.as_retriever(search_kwargs={"k": 3}).invoke(user_question)
            context = "\n".join([d.page_content for d in docs])
        else:
            context = "Use general knowledge or the conversation history provided below."

        # 4. Tone & Personality Application
        personality = self._get_personality()
        
        # 5. THE FINAL PROMPT (The "Brain" of the response)
        final_prompt = f"""
        Role: {personality}
        
        [CONVERSATION HISTORY]
        {formatted_history if formatted_history else "This is the start of the conversation."}
        
        [PERMANENT COMPANY CONTEXT]
        {context}
        
        [TEMPORARY UPLOADED FILE CONTEXT]
        {extra_context if extra_context else "No temporary files uploaded."}
        
        [USER QUESTION]
        {user_question}
        
        Instructions:
        1. Check [CONVERSATION HISTORY] first. If the user already provided info (like their name or username), use it!
        2. If the answer is in the [TEMPORARY UPLOADED FILE CONTEXT], prioritize that for specific document questions.
        3. Use the [PERMANENT COMPANY CONTEXT] for general company rules.
        4. If you still don't know, honestly state you don't have that information.
        """
        
        response = self.llm.invoke(final_prompt)
        
        return {
            "answer": response.content,
            "sources": [d.metadata.get('source', 'Unknown') for d in docs],
            "used_kb": "YES" in decision_resp or len(extra_context) > 0
        }
