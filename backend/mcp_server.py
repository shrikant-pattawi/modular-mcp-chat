import os
import sqlite3
import datetime
from pathlib import Path
from mcp.server.mcpserver import MCPServer

# Initialize MCP Server instance
server = MCPServer("TimeAndDatabaseTools")

DB_PATH = Path(__file__).resolve().parent / "app_data.db"

def init_sample_database():
    """Initializes a sample SQLite database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL
    );
    """)
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ("MacBook Pro M3", "Electronics", 1999.99, 15),
            ("Dell XPS 15", "Electronics", 1499.00, 22),
            ("Sony WH-1000XM5 Headphones", "Audio", 399.99, 45),
            ("Logitech MX Master 3S Mouse", "Accessories", 99.99, 80),
            ("Ergonomic Office Chair", "Furniture", 299.50, 10),
            ("4K Ultra-Wide Monitor", "Displays", 549.00, 18)
        ]
        cursor.executemany("INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)", products)
        
        users = [
            ("Alice Johnson", "Lead Developer", "Engineering"),
            ("Bob Smith", "Product Manager", "Product"),
            ("Charlie Davis", "Data Scientist", "Analytics"),
            ("Diana Prince", "Security Engineer", "Security")
        ]
        cursor.executemany("INSERT INTO users (name, role, department) VALUES (?, ?, ?)", users)
        conn.commit()
        
    conn.close()

init_sample_database()

@server.tool()
def get_current_time(timezone_name: str = "UTC") -> str:
    """
    Returns the current date and time.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return f"Current UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

@server.tool()
def list_database_tables() -> str:
    """
    Lists all available tables and schemas in the local SQLite database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    conn.close()
    
    if not tables:
        return "No user tables found in database."
    
    output = "Available Database Tables:\n"
    for name, schema in tables:
        output += f"\nTable '{name}':\nSchema: {schema}\n"
    return output

@server.tool()
def query_database(sql_query: str) -> str:
    """
    Executes a SELECT SQL query on the local SQLite database and returns the rows.
    """
    cleaned_sql = sql_query.strip().upper()
    if not cleaned_sql.startswith("SELECT") and not cleaned_sql.startswith("PRAGMA") and not cleaned_sql.startswith("EXPLAIN"):
        return "Error: Only read-only SELECT queries are permitted on this database."

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description] if cursor.description else []
        conn.close()

        if not rows:
            return "Query executed successfully. 0 rows returned."

        header = " | ".join(column_names)
        separator = " | ".join(["---"] * len(column_names))
        row_lines = [" | ".join(str(cell) for cell in row) for row in rows]
        
        return f"| {header} |\n| {separator} |\n" + "\n".join(f"| {line} |" for line in row_lines)
    except Exception as e:
        return f"Database Query Error: {str(e)}"

if __name__ == "__main__":
    server.run()

