# Modular MCP Chat Application

A modular, full-stack chat application built with **FastAPI**, **Google Gemini (`google-genai`)**, **Model Context Protocol (MCP)**, and a custom **Tailwind CSS** frontend.

---

## Architecture & Project Structure

This project follows a strict modular design pattern to separate concerns between HTTP routing, LLM processing, MCP tool execution, and frontend UI rendering.

```text
modular-mcp-chat/
├── backend/
│   ├── main.py          # FastAPI application & lifespan management
│   ├── llm_service.py   # Google Gemini API integration & tool calling loop
│   ├── mcp_client.py    # MCP Client manager connecting via stdio transport
│   ├── mcp_server.py    # MCP Server providing Time and SQLite Database tools
│   ├── app_data.db      # Local SQLite database (seeded with products & users)
│   ├── requirements.txt # Python dependencies
│   └── .env             # Environment variables (Gemini API key)
├── frontend/
│   ├── index.html       # HTML structure with Tailwind CSS CDN
│   ├── css/
│   │   └── styles.css   # Custom scrollbars & bubble animations
│   └── js/
│       └── chat_logic.js# Asynchronous fetch logic & DOM manipulation
├── .gitignore
└── README.md
```

---

## Tools Provided by MCP Server

The application includes an MCP tool server (`backend/mcp_server.py`) exposing:
1. **`get_current_time(timezone_name)`**: Fetches live UTC/local time.
2. **`list_database_tables()`**: Discovers available tables and schema in the SQLite database.
3. **`query_database(sql_query)`**: Executes read-only SQL queries against the local `app_data.db` database (seeded with sample products and users).

---

## Setup & Running Instructions

### 1. Prerequisites
- Python 3.10 or higher.
- Free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Backend Setup
1. Open a terminal in the project root directory.
2. Activate your virtual environment:
   - **PowerShell (Windows):** `.\venv\Scripts\Activate.ps1`
   - **CMD (Windows):** `.\venv\Scripts\activate.bat`
   - **Linux/macOS:** `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Configure your API key in `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
5. Start the FastAPI backend server:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   The backend API will run at `http://127.0.0.1:8000`. You can inspect the Swagger API docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
1. Navigate to the `frontend/` directory or serve static files:
   ```bash
   cd frontend
   python -m http.server 3000
   ```
2. Open your browser and navigate to `http://localhost:3000` (or simply open `frontend/index.html` directly in your web browser).

---

## Example Prompts to Test Live MCP Tools

Try typing these into the chat interface:
- *"What is the current UTC time?"* *(Invokes `get_current_time`)*
- *"What tables do we have in our database?"* *(Invokes `list_database_tables`)*
- *"What are the 3 most expensive products in our inventory?"* *(Invokes `query_database` with `SELECT name, price FROM products ORDER BY price DESC LIMIT 3`)*
- *"Show me all employees in the Engineering department."* *(Invokes `query_database`)*
