# mcp_server.py
import requests
from bs4 import BeautifulSoup
import re
from fastmcp import FastMCP

mcp = FastMCP("Dataquartz Librarian")

# --- 1. THE CALLABLE LOGIC ---
# Keep this outside or as a static method so Streamlit can call it easily.
def scrape_dataquartz(query: str) -> str:
    url = "https://dataquartz.com" 
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Clean up noise
        for element in soup(["script", "style", "nav", "footer"]):
            element.extract()
        text = soup.get_text(separator=' ')
        
        # Simple keyword matching
        keywords = query.lower().split()
        sentences = re.split(r'(?<=[.!?]) +', text)
        relevant = [s.strip() for s in sentences if any(k in s.lower() for k in keywords)]
        
        return "\n".join(relevant[:5]) if relevant else "No live matches found."
    except Exception as e:
        return f"Scraper error: {str(e)}"

# --- 2.TOOL REGISTRATION ---

    @mcp.tool()
    def search_dataquartz(query: str) -> str:
        # We call the external logic function here
        return scrape_dataquartz(query)
