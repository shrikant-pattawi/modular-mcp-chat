import os
import asyncio
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from backend.mcp_client import mcp_manager

logger = logging.getLogger(__name__)

def _reload_env():
    current_dir = Path(__file__).resolve().parent
    backend_env = current_dir / ".env"
    root_env = current_dir.parent / ".env"
    
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=True)

# Tool bridge functions for Gemini automatic function execution
async def get_current_time(timezone_name: str = "UTC") -> str:
    """Returns the current date and time in UTC or local timezone."""
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("get_current_time", {"timezone_name": timezone_name})
    now = datetime.datetime.now(datetime.timezone.utc)
    return f"Current UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

async def list_database_tables() -> str:
    """Lists all available tables and schemas in the local SQLite database."""
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("list_database_tables", {})
    return "Error: MCP Server is offline."

async def query_database(sql_query: str) -> str:
    """Executes a read-only SELECT SQL query on the local database and returns the records."""
    if mcp_manager and mcp_manager.is_connected:
        return await mcp_manager.call_tool("query_database", {"sql_query": sql_query})
    return "Error: MCP Server is offline."

async def get_llm_response(prompt: str, history: Optional[List[Dict[str, str]]] = None, manager=None) -> str:
    """
    Sends a user prompt to Gemini API with conversation history, automatic tool execution, and retry backoff.
    """
    _reload_env()
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or gemini_key.strip() == "" or gemini_key == "your_gemini_api_key_here":
        return "Error: GEMINI_API_KEY is missing or set to default in backend/.env. Get a free key at https://aistudio.google.com/app/apikey"

    client = genai.Client(api_key=gemini_key.strip())
    tools = [get_current_time, list_database_tables, query_database]

    # Convert past history to Gemini Content objects
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

    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    max_retries = 3

    for attempt in range(max_retries):
        for model_name in models_to_try:
            try:
                chat_kwargs: Dict[str, Any] = {
                    "model": model_name,
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
                logger.warning(f"Attempt {attempt+1} on model {model_name} failed: {error_msg}")
                
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(4 * (attempt + 1))
                        continue
                elif "404" in error_msg or "NOT_FOUND" in error_msg:
                    continue
                else:
                    return f"Error communicating with Gemini LLM: {error_msg}"

    return "⏳ The API is currently busy under free-tier limits. Please wait 15–20 seconds and try again."
