# mcp_server.py
import requests
from bs4 import BeautifulSoup
import re
from fastmcp import FastMCP

mcp = FastMCP("Dataquartz Librarian")

# --- 1. THE CALLABLE LOGIC ---
# Keep this outside or as a static method so Streamlit can call it easily.
def scrape_dataquartz(query: str) -> str:
    """
    Agent Tool: Searches the Dataquartz website and extracts chunks relevant to the query.
    """
    url = "https://dataquartz.com" 
    headers = {"User-Agent": "DataquartzBot/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Aggressive Noise Reduction
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.extract()

        # 2. Extract meaningful text blocks (not just one long string)
        # We look for paragraphs and list items where the real info lives
        text_blocks = [tag.get_text(separator=' ', strip=True) 
                       for tag in soup.find_all(['p', 'li', 'h1', 'h2', 'h3'])]
        
        # 3. Smart Relevance Filtering
        keywords = [k.lower() for k in query.split() if len(k) > 3] # Filter out 'the', 'is', etc.
        if not keywords: keywords = [query.lower()]
            
        relevant_chunks = []
        for block in text_blocks:
            if any(k in block.lower() for k in keywords):
                relevant_chunks.append(block)

        # 4. Result Logic
        if relevant_chunks:
            # Return top 4 most relevant chunks to stay within context limits
            return "\n\n---\n\n".join(relevant_chunks[:4])
        
        # Fallback: If no keywords match, return the first few paragraphs so the AI has context
        return "No direct keyword match. General site context: " + " ".join(text_blocks[:3])

    except Exception as e:
        return f"Scraper error: {str(e)}"
# --- 2.TOOL REGISTRATION ---

    @mcp.tool()
    def search_dataquartz(query: str) -> str:
        # We call the external logic function here
        return scrape_dataquartz(query)
