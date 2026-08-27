import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

SERVER_SCRIPT = str(Path(__file__).resolve().parent / "mcp_server.py")

class MCPClientManager:
    """
    Manages connection and interaction with the local MCP server over stdio transport.
    """
    def __init__(self, command: Optional[str] = None, args: Optional[List[str]] = None):
        self.command = command or sys.executable
        self.args = args if args is not None else [SERVER_SCRIPT]
        self.session: Optional[ClientSession] = None
        self._client_context = None
        self.is_connected = False

    async def connect(self):
        """
        Connect to the MCP server. If connection fails, log error and maintain graceful offline state.
        """
        try:
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=dict(os.environ)
            )
            # Enter stdio client context
            self._client_context = stdio_client(server_params)
            read_stream, write_stream = await self._client_context.__aenter__()
            
            # Initialize ClientSession
            self.session = ClientSession(read_stream, write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            
            self.is_connected = True
            logger.info("Successfully connected to MCP Server.")
        except Exception as e:
            self.is_connected = False
            logger.warning(f"Could not connect to MCP Server: {e}. Running in standalone LLM mode.")

    async def get_tools(self) -> List[Dict[str, Any]]:
        """
        Retrieve available tools from the connected MCP Server.
        """
        if not self.is_connected or not self.session:
            return []
        
        try:
            tools_result = await self.session.list_tools()
            formatted_tools = []
            for tool in tools_result.tools:
                formatted_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema if hasattr(tool, "inputSchema") and tool.inputSchema else {"type": "object", "properties": {}}
                })
            return formatted_tools
        except Exception as e:
            logger.error(f"Error fetching MCP tools: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool on the MCP server.
        """
        if not self.is_connected or not self.session:
            return f"Error: MCP Server is offline. Cannot execute tool '{tool_name}'."

        try:
            result = await self.session.call_tool(tool_name, arguments)
            # Extract content from TextContent objects
            content_texts = []
            for item in result.content:
                if hasattr(item, "text"):
                    content_texts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    content_texts.append(item["text"])
                else:
                    content_texts.append(str(item))

            return "\n".join(content_texts) if content_texts else "Tool executed with no output."
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    async def close(self):
        """
        Cleanly close session if connected.
        """
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")
        finally:
            self.session = None
            self._client_context = None
            self.is_connected = False
            logger.info("MCP Client connection closed.")

# Global instance for FastAPI lifespan
mcp_manager = MCPClientManager()
