import os
import json
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

async def _call_openai_fallback(prompt: str, history: Optional[List[Dict[str, str]]], openai_key: str) -> str:
    """Fallback handler using OpenAI GPT-4o-mini with MCP tools."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=openai_key)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": "You are a helpful AI assistant with access to local database and clock tools. Use tools when relevant."}
        ]
        if history:
            for item in history:
                role = "assistant" if item.get("role") in ["assistant", "model"] else "user"
                messages.append({"role": role, "content": item.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Returns current UTC or local timezone time",
                    "parameters": {
                        "type": "object",
                        "properties": {"timezone_name": {"type": "string", "default": "UTC"}}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_database_tables",
                    "description": "Lists all available tables and schemas in SQLite database",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_database",
                    "description": "Executes read-only SELECT SQL query on database",
                    "parameters": {
                        "type": "object",
                        "properties": {"sql_query": {"type": "string"}},
                        "required": ["sql_query"]
                    }
                }
            }
        ]

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        choice = response.choices[0].message

        # Handle tool calls if requested
        if choice.tool_calls:
            messages.append(choice)
            for tool_call in choice.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except Exception:
                    args = {}

                if name == "get_current_time":
                    tool_output = await get_current_time(**args)
                elif name == "list_database_tables":
                    tool_output = await list_database_tables()
                elif name == "query_database":
                    tool_output = await query_database(**args)
                else:
                    tool_output = f"Unknown tool: {name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output
                })

            second_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            return second_response.choices[0].message.content or "No response from OpenAI."

        return choice.content or "No response from OpenAI."

    except Exception as e:
        logger.error(f"OpenAI fallback error: {e}")
        return f"Both Gemini and OpenAI requests failed. OpenAI error: {str(e)}"

async def get_llm_response(prompt: str, history: Optional[List[Dict[str, str]]] = None, manager=None) -> str:
    """
    Primary: Google Gemini API.
    Automatic Fallback: OpenAI GPT-4o-mini (if OPENAI_API_KEY is configured in .env).
    """
    _reload_env()
    
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Step 1: Try Primary Provider (Google Gemini)
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
            logger.warning(f"Primary Gemini call failed: {error_msg}. Checking for OpenAI fallback...")

            # Step 2: If OpenAI Key is available, trigger fallback
            if openai_key and openai_key != "your_openai_api_key_here":
                logger.info("Executing automatic fallback to OpenAI (gpt-4o-mini)...")
                return await _call_openai_fallback(prompt, history, openai_key)

            # If no OpenAI key, return quota guidance
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return (
                    "⏳ Gemini Quota Reached.\n\n"
                    "Tip: You can either wait ~45s for the free-tier reset, or add `OPENAI_API_KEY` to `backend/.env` for automatic instant failover!"
                )
            return f"Error communicating with Gemini: {error_msg}"

    # Step 3: If Gemini key is not set, but OpenAI key is set
    if openai_key and openai_key != "your_openai_api_key_here":
        return await _call_openai_fallback(prompt, history, openai_key)

    return "Error: No valid API key configured. Please set GEMINI_API_KEY or OPENAI_API_KEY in backend/.env"
