🤖 Dataquartz AI Ecosystem
A high-performance AI assistant for Dataquartz, using the Model Context Protocol (MCP) to ground LLM responses in real-time web data.

🛠️ Tech Stack
Frontend: Streamlit (Custom CSS & Glassmorphism)

LLM: Groq (Llama 3.3 70B)

Database: Supabase (PostgreSQL for history)

Storage: Supabase CDN (Assets & 4K Video)

Protocol: MCP (Real-time web scraping tool-calling)

🏗️ Architecture
User Query: User asks about Dataquartz products.

MCP Tool Call: AI invokes scrape_dataquartz tool.

Real-time Scraping: Server fetches live data from dataquartz.com.

Grounded Response: AI answers using fresh site context to prevent hallucinations.

🚀 Setup
Secrets (.streamlit/secrets.toml):

Ini, TOML
GROQ_API_KEY = "your_key"
SUPABASE_URL = "your_url"
SUPABASE_KEY = "your_anon_key"
Install: pip install streamlit supabase langchain-groq mcp beautifulsoup4

Run: streamlit run main_app.py

📂 Project Structure
main_app.py: The navigation hub with glowing UI components.

pages/1_Chatbot.py: The AI interface with persistent memory and video background.

mcp_server.py: Bridge logic for live data extraction.

database.py: CRUD operations for session management.

🎨 Design
Font: Electrolize

Theme: Deep Space Black with Cyan (#00FFFF) and Purple (#9D00FF) accents.

Effects: Inset border shine and hover-glow on all interactive elements.
