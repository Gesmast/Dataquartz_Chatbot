from fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import re
from fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("Dataquartz Librarian")

# --- 1. THE RAW LOGIC (Callable by Streamlit & AI) ---
def scrape_dataquartz(query: str) -> str:
    """
    Cleaned logic to search and scrape dataquartz.com.
    Separated from the decorator to prevent 'TypeError: not callable' in Streamlit.
    """
    url = "https://dataquartz.com" 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Request with a timeout and a browser-like header to avoid 403 blocks
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noisy elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.extract()
            
        text = soup.get_text(separator=' ')
        
        # Logic: Find sentences containing the user's keywords
        keywords = query.lower().split()
        # Split into sentences while keeping punctuation
        sentences = re.split(r'(?<=[.!?]) +', text)
        
        # Filter for relevance
        relevant_matches = [
            s.strip() for s in sentences 
            if any(k in s.lower() for k in keywords) and len(s.strip()) > 10
        ]
        
        if not relevant_matches:
            return f"No specific mention of '{query}' found on the live site. Do not hallucinate."

        return "\n".join(relevant_matches[:10])
    
    except requests.exceptions.RequestException as e:
        return f"System Error: Could not reach Dataquartz.com. Details: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"

# --- 2. THE MCP TOOL WRAPPER (Exposed to the LLM) ---
@mcp.tool()
def search_dataquartz(query: str) -> str:
    """
    Mandatory tool for ANY question about Dataquartz, its products (like QuartzGPT, SuppluSense), 
    services, or company info. Use this to find live facts before answering.
    """
    return scrape_dataquartz(query)
