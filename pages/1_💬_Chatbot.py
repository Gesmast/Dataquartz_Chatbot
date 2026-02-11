import streamlit as st
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool

# Project Imports
from database import create_new_session, save_message, get_chat_history
from Calmcp import get_available_slots, create_cal_booking

# --- CONFIGURATION ---
LLM_MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT_FILE = "SystemPrompt.txt"  # File in same repo directory


# --- HELPER FUNCTIONS ---
def load_system_prompt() -> str:
    """Load system prompt from file in the repository."""
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        prompt_path = script_dir / SYSTEM_PROMPT_FILE
        
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8').strip()
        else:
            st.error(f"System prompt file not found: {SYSTEM_PROMPT_FILE}")
            return "You are the Dataquartz AI assistant."
    except Exception as e:
        st.error(f"Error loading system prompt: {e}")
        return "You are the Dataquartz AI assistant."


def get_cal_tools():
    """Create LangChain tools for Cal.com integration."""
    return [
        StructuredTool.from_function(
            coroutine=get_available_slots,
            name="get_available_slots",
            description="Finds open booking times for a specific date (YYYY-MM-DD format)."
        ),
        StructuredTool.from_function(
            coroutine=create_cal_booking,
            name="create_cal_booking",
            description="Books a meeting. Requires email, name, and start_time (ISO format)."
        )
    ]


@asynccontextmanager
async def mcp_session() -> AsyncGenerator[ClientSession, None]:
    """Context manager for MCP server connection."""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def get_mcp_tools() -> list:
    """Load tools from MCP server."""
    async with mcp_session() as session:
        return await load_mcp_tools(session)


async def create_agent_with_tools():
    """Initialize the agent with both MCP and Cal tools."""
    # Load MCP tools
    mcp_tools = await get_mcp_tools()
    
    # Combine with Cal tools
    all_tools = mcp_tools + get_cal_tools()
    
    # Load system prompt
    system_prompt = load_system_prompt()
    
    # Initialize LLM
    llm = ChatGroq(model=LLM_MODEL, temperature=0)
    
    # Create agent
    agent = create_react_agent(
        llm, 
        tools=all_tools, 
        state_modifier=system_prompt
    )
    
    return agent


async def run_agent(agent, user_message: str) -> str:
    """Execute the agent with the user message."""
    # Prepare inputs
    inputs = {"messages": [HumanMessage(content=user_message)]}
    
    # Invoke agent
    result = await agent.ainvoke(inputs)
    
    return result["messages"][-1].content


def run_async(coro):
    """Helper to run async functions in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# --- SESSION STATE INITIALIZATION ---
if "agent" not in st.session_state:
    with st.spinner("Connecting to Knowledge Base MCP..."):
        try:
            st.session_state.agent = run_async(create_agent_with_tools())
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.stop()

if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = get_chat_history(st.session_state.session_id)


# --- UI RENDERING ---
st.title("Dataquartz AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- CHAT LOGIC ---
if prompt := st.chat_input("How can I help you today?"):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Agent Execution
    with st.chat_message("assistant"):
        with st.spinner("Searching Knowledge Base..."):
            try:
                # Run agent
                answer = run_async(run_agent(st.session_state.agent, prompt))
                
                st.markdown(answer)
                
                # 3. Save History
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message(st.session_state.session_id, "assistant", answer)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                save_message(st.session_state.session_id, "assistant", error_msg)
