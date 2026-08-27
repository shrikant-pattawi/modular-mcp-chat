from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.llm_service import get_llm_response
from backend.mcp_client import mcp_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MCP client connection
    await mcp_manager.connect()
    yield
    # Shutdown: Cleanly close MCP connection
    await mcp_manager.close()

app = FastAPI(title="Modular MCP Chat API", lifespan=lifespan)

# CORS middleware for browser frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    bot_reply = await get_llm_response(
        prompt=payload.message,
        history=payload.history,
        manager=mcp_manager
    )
    return ChatResponse(response=bot_reply)