import os
import asyncio
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def _reload_env():
    current_dir = Path(__file__).resolve().parent
    backend_env = current_dir / ".env"
    root_env = current_dir.parent / ".env"
    
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=True)

# Tool bridge functions for MCP execution
async def get_current_time(timezone_name: str = "UTC") -> str:
    """Returns current date and time in UTC or local timezone."""
    from backend.mcp_client import mcp_manager
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("get_current_time", {"timezone_name": timezone_name})
    now = datetime.datetime.now(datetime.timezone.utc)
    return f"Current UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

async def list_database_tables() -> str:
    """Lists all available tables and schemas in the local SQLite database."""
    from backend.mcp_client import mcp_manager
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("list_database_tables", {})
    return "Error: MCP Server is offline."

async def query_database(sql_query: str) -> str:
    """Executes a read-only SELECT SQL query on the local database and returns the records."""
    from backend.mcp_client import mcp_manager
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("query_database", {"sql_query": sql_query})
    return "Error: MCP Server is offline."

async def get_llm_response(prompt: str, history: Optional[List[Dict[str, str]]] = None, manager=None) -> str:
    """
    Sends a user prompt to Gemini API (or Groq / OpenAI fallback) with automatic tool execution.
    """
    _reload_env()
    
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Priority 1: Google Gemini API
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            tools = [get_current_time, list_database_tables, query_database]

            past_contents = []
            if history:
                for item in history:
                    role = "user" if item.get("role") == "user" else "model"
                    text_val = item.get("content", "")
                    if text_val:
                        past_contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=text_val)]
                            )
                        )

            chat_kwargs: Dict[str, Any] = {
                "model": "gemini-3.6-flash",
                "config": {
                    "tools": tools,
                    "system_instruction": (
                        "You are a helpful AI assistant with access to local SQLite database tools and real-time clock tools. "
                        "When the user asks about database records (products, users) or current time, call the appropriate tools."
                    )
                }
            }
            if past_contents:
                chat_kwargs["history"] = past_contents

            chat = client.aio.chats.create(**chat_kwargs)
            response = await chat.send_message(prompt)
            if response.text:
                return response.text

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Gemini API call failed: {error_msg}")
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                # If Groq or OpenAI key is not provided, inform user clearly
                if (not groq_key or groq_key == "your_groq_api_key_here") and (not openai_key or openai_key == "your_openai_api_key_here"):
                    return (
                        "⏳ Gemini Daily/Minute Quota Reached.\n\n"
                        "Options:\n"
                        "1. Wait ~45 seconds for per-minute reset.\n"
                        "2. Or generate a fresh free Gemini key at https://aistudio.google.com/app/apikey (choose 'Create API key in new project')."
                    )

    return "Error: No valid API key configured. Please set GEMINI_API_KEY in backend/.env"
