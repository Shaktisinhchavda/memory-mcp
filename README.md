# 🧠 Personal MCP Ecosystem

A modular, local-first infrastructure that exposes your personal data — files, notes, browser history, code activity, conversations — as unified semantic context via the **Model Context Protocol (MCP)**.

Any AI agent can plug into this and instantly know you.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![MCP](https://img.shields.io/badge/MCP-stdio-green)
![Neo4j](https://img.shields.io/badge/Neo4j-5-blue?logo=neo4j)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

| Capability | Description |
|------------|-------------|
| **Semantic Search** | Query your notes by meaning using ChromaDB + sentence-transformers |
| **Knowledge Graph** | Neo4j-backed entity extraction with relationship mapping |
| **File Reader** | Read PDFs, DOCX, Markdown, code files from anywhere on disk |
| **Browser History** | Search your Chrome browsing history |
| **Code Activity** | Git commits, repo stats, and VSCode recent files |
| **Conversations** | Search exported Claude & ChatGPT conversations |
| **Event Logger** | Real-time file change tracking via watchdog |
| **Unified Gateway** | FastAPI + LangGraph agent that routes queries across all sources |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Unified Gateway (:8000)                    │
│              FastAPI + LangGraph Agent Pipeline               │
│           analyze → execute → aggregate → rank                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Core MCP │ │Files MCP │ │ Browser  │ │   Code MCP     │  │
│  │          │ │          │ │   MCP    │ │                │  │
│  │• Notes   │ │• PDF     │ │• Chrome  │ │• Git commits   │  │
│  │• Search  │ │• DOCX    │ │  History │ │• Repo stats    │  │
│  │• Events  │ │• Text    │ │• Stats   │ │• VSCode recent │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│                                                              │
│  ┌──────────────────┐ ┌──────────────────────────────────┐   │
│  │ Conversations MCP│ │ Knowledge Graph MCP              │   │
│  │                  │ │                                  │   │
│  │• Claude exports  │ │• Entity extraction               │   │
│  │• ChatGPT exports │ │• Graph search (Neo4j)            │   │
│  │• Search & parse  │ │• Path finding                    │   │
│  └──────────────────┘ └──────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ ChromaDB (vectors)  │ Neo4j (graph)  │ SQLite (events)      │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Docker](https://www.docker.com/) — for Neo4j (optional)
- Google Chrome — for browser history (optional)

### 1. Clone & Install

```bash
git clone https://github.com/Shaktisinhchavda/memory-mcp.git
cd memory-mcp
uv sync
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings (defaults work out of the box)
```

### 3. Add Your Notes

Place markdown or text files in `data/notes/`:

```bash
# Example
echo "# My Project Ideas" > data/notes/ideas.md
```

### 4. Index & Build

```bash
# Index notes into ChromaDB vector store
uv run python scripts/index_notes.py

# Start Neo4j (optional — for knowledge graph)
docker compose up -d

# Build knowledge graph from notes
uv run python scripts/build_graph.py
```

### 5. Run

**Option A — Claude Desktop Integration (recommended)**

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "core_mcp/server.py"]
    },
    "files-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "connectors/files_mcp/server.py"]
    },
    "browser-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "connectors/browser_mcp/server.py"]
    },
    "code-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "connectors/code_mcp/server.py"]
    },
    "conversations-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "connectors/conversations_mcp/server.py"]
    },
    "graph-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\memory-mcp", "run", "python", "knowledge_graph/server.py"]
    }
  }
}
```

Restart Claude Desktop. You'll see the 🔨 icon.

**Option B — Unified Gateway (HTTP API)**

```bash
uv run uvicorn gateway.server:app --host 0.0.0.0 --port 8000
```

Open Swagger UI at `http://localhost:8000/docs`.

## 🛠️ Tools Reference

### Core MCP (4 tools)
| Tool | Description |
|------|-------------|
| `read_notes` | List and read personal notes |
| `semantic_search` | Query knowledge base by meaning |
| `get_recent_activity` | Recent file change events |
| `index_stats` | Vector store diagnostics |

### Files MCP (3 tools)
| Tool | Description |
|------|-------------|
| `read_local_file` | Read PDF, DOCX, text files |
| `list_local_files` | List files in a directory |
| `search_local_files` | Search by filename pattern |

### Browser MCP (4 tools)
| Tool | Description |
|------|-------------|
| `recent_browsing_history` | Recent Chrome history |
| `most_visited_sites` | Top sites by visit count |
| `search_browsing_history` | Search by keyword |
| `browsing_stats` | Overall browsing stats |

### Code MCP (5 tools)
| Tool | Description |
|------|-------------|
| `recent_commits` | Git commit history |
| `commit_details` | Single commit details |
| `git_status` | Modified/staged/untracked files |
| `repo_statistics` | Repo stats and contributors |
| `vscode_recent` | Recently opened in VSCode |

### Conversations MCP (3 tools)
| Tool | Description |
|------|-------------|
| `list_conversation_exports` | List exported JSON files |
| `read_conversations` | Parse Claude/ChatGPT exports |
| `search_in_conversations` | Search by keyword |

### Knowledge Graph MCP (4 tools)
| Tool | Description |
|------|-------------|
| `graph_search` | Find entity and its connections |
| `find_connection` | Shortest path between entities |
| `graph_stats` | Node/relationship counts |
| `ingest_file` | Extract entities into graph |

## 📁 Project Structure

```
memory-mcp/
├── core_mcp/                 # Phase 1 — Core MCP server
│   ├── server.py             # Main MCP server (stdio)
│   ├── tools/                # Notes + search tools
│   ├── vector_store/         # ChromaDB integration
│   └── event_logger/         # File watcher + SQLite
├── connectors/               # Phase 2 — Data connectors
│   ├── files_mcp/            # PDF, DOCX, text reader
│   ├── browser_mcp/          # Chrome history
│   ├── calendar_mcp/         # Google Calendar (OAuth)
│   ├── code_mcp/             # Git + VSCode activity
│   └── conversations_mcp/    # Claude/ChatGPT exports
├── knowledge_graph/          # Phase 3 — Neo4j graph
│   ├── extractor.py          # Entity extraction
│   ├── graph_store.py        # Neo4j CRUD + search
│   └── server.py             # Graph MCP server
├── gateway/                  # Phase 4 — Unified gateway
│   ├── agent.py              # LangGraph orchestrator
│   ├── router.py             # Smart query router
│   ├── ranker.py             # Multi-signal ranking
│   ├── context.py            # PersonalContext model
│   └── server.py             # FastAPI gateway
├── scripts/                  # Utility scripts
│   ├── index_notes.py        # Build vector index
│   ├── build_graph.py        # Build knowledge graph
│   └── start_watcher.py      # Start file watcher
├── data/                     # Your personal data (git-ignored)
│   ├── notes/                # Markdown notes
│   ├── files/                # Documents
│   └── conversations/        # Exported AI chats
├── docker-compose.yml        # Neo4j container
├── pyproject.toml            # Dependencies
└── .env.example              # Config template
```

## 🔒 Privacy

- **100% local-first** — all processing runs on your machine
- **No cloud APIs required** — embeddings, search, and graph are local
- **Personal data never committed** — `data/` is git-ignored
- **Secrets excluded** — `.env`, credentials, and tokens are git-ignored

## 📄 License

MIT
