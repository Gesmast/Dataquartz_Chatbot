from fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import re

mcp = FastMCP("Dataquartz Librarian")

@mcp.tool()
def search_dataquartz(query: str) -> str:
    """
    Mandatory tool for ANY question about Dataquartz, its products (like QuartzGPT, SuppluSense), 
    services, or company info. Use this to find live facts before answering.
    """
    url = "https://dataquartz.com" 
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Clean up the site text
        for element in soup(["script", "style", "nav", "footer"]):
            element.extract()
        text = soup.get_text(separator=' ')
        
        # Logic: Find sentences containing the user's keywords
        keywords = query.lower().split()
        sentences = re.split(r'(?<=[.!?]) +', text)
        relevant_matches = [s for s in sentences if any(k in s.lower() for k in keywords)]
        
        if not relevant_matches:
            return f"No specific mention of '{query}' found on the live site. Stick to the facts: do not hallucinate."

        return "\n".join(relevant_matches[:10]) # Return top 10 relevant snippets
    
    except Exception as e:
        return f"System Error: Could not reach Dataquartz.com. {str(e)}"
