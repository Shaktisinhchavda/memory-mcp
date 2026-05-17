# 🧠 Personal MCP Ecosystem

> A modular, local-first infrastructure that exposes your personal data as unified semantic context via the Model Context Protocol (MCP). Any AI agent can plug in and instantly know you.

**Everything runs locally. No data leaves your machine.**

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Desktop │     │   Claude Code   │     │  Any MCP Client │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │ stdio                 │ stdio                  │ stdio
         └───────────────┬───────┴────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   MCP Server        │
              │   (FastMCP)         │
              │                     │
              │  Tools:             │
              │  • read_notes       │
              │  • semantic_search  │
              │  • get_activity     │
              │  • index_stats      │
              └──┬──────┬──────┬───┘
                 │      │      │
        ┌────────▼┐  ┌──▼───┐  ┌▼────────┐
        │ Notes   │  │Vector│  │ Event   │
        │ Reader  │  │Store │  │ Logger  │
        │         │  │Chroma│  │ SQLite  │
        └────┬────┘  └──┬───┘  └──┬──────┘
             │          │         │
        ┌────▼──────────▼─────────▼──┐
        │     data/notes  data/files │
        └────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Install dependencies
```bash
cd d:\memory-mcp
uv sync
```

### 2. Index your notes
```bash
uv run python scripts/index_notes.py
```

### 3. Run tests
```bash
uv run python tests/test_notes.py
uv run python tests/test_search.py
uv run python tests/test_watcher.py
```

### 4. Test with MCP Inspector
```bash
uv run mcp dev core_mcp/server.py
```

### 5. Connect to Claude Desktop
Add this to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "core_mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop, then try:
- *"What notes do I have?"*
- *"Search my notes for AI project ideas"*
- *"Read my meeting notes"*

### 6. Start the file watcher (separate terminal)
```bash
uv run python scripts/start_watcher.py
```

## 📁 Project Structure

```
memory-mcp/
├── pyproject.toml          # uv project config
├── .env                    # environment variables
├── config/                 # pydantic settings
├── core_mcp/               # Phase 1: Core MCP Server
│   ├── server.py           # FastMCP server entry point
│   ├── tools/              # MCP tool implementations
│   │   ├── notes.py        # read_notes tool
│   │   └── search.py       # semantic_search tool
│   ├── vector_store/       # ChromaDB wrapper
│   │   ├── store.py        # Vector store operations
│   │   └── indexer.py      # Document indexing pipeline
│   └── event_logger/       # File system monitoring
│       ├── watcher.py      # watchdog observer
│       └── database.py     # SQLite event storage
├── data/                   # Your personal data
│   ├── notes/              # Markdown notes
│   └── files/              # General files
├── scripts/                # Utility scripts
└── tests/                  # Test suite
```

## 🔧 MCP Tools

| Tool | Description |
|------|-------------|
| `read_notes(filename?)` | List all notes or read a specific one |
| `semantic_search(query, top_k?)` | Search notes by meaning using embeddings |
| `get_recent_activity(limit?)` | See recent file changes |
| `index_stats()` | Check vector store status |

## 📋 Roadmap

- [x] **Phase 1** — Core Foundation (MCP Server + Vector Store + Event Logger)
- [ ] **Phase 2** — Data Connectors (files, browser, calendar, code, conversations)
- [ ] **Phase 3** — Knowledge Graph (Neo4j entity extraction)
- [ ] **Phase 4** — Unified Gateway (LangGraph agent + context ranking)

## License
MIT
