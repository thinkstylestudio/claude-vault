# Claude Vault

Transform your AI coding conversations into a searchable, organized knowledge base in Obsidian.

## What is Claude Vault?

Claude Vault is a command-line tool that syncs your AI coding assistant conversations into beautifully formatted Markdown files that integrate seamlessly with Obsidian and other note-taking tools.

## Supported Sources

- **Claude Web** (.json) — Exported from claude.ai settings
- **Claude Code** (.jsonl) — From Claude Code CLI `~/.claude` folder
- **OpenCode** (.db) — From OpenCode SQLite database

## Features

- ✅ **Local-first**: Your conversations, your vault, your control
- ✅ **Simple CLI**: Easy to use, powerful features
- ✅ **Bulk Historical Import**: Import your entire conversation history at once
- ✅ **Obsidian-native**: Full frontmatter, tags, and metadata support
- ✅ **AI-Powered Tagging & Summarization**: Automatic generation of tags and summaries using local LLMs (Ollama) - no API costs
- ✅ **Auto-Sync with Watch Mode**: Real-time syncing when conversation files change
- ✅ **Semantic Search**: AI-powered search by meaning, not just keywords
- ✅ **Bi-directional sync**: Rename and move files freely - they stay in sync
- ✅ **Smart updates**: Only syncs what's changed
- ✅ **UUID tracking**: Maintains file relationships even after renaming
- ✅ **Cross-Conversation Search**: Search across all conversations with context and navigate to related ones
- ✅ **Smart Relationship Detection**: Automatically finds and links related conversations via common tags

## How it Works

Claude Vault uses a modular architecture to handle different conversation formats:

1.  **Format Detection**: Automatically identifies if a file is a Web export (`.json`), Code History (`.jsonl`), or OpenCode database (`.db`).
2.  **Parsing**: Specialized parsers (`parser.py`, `code_parser.py`, `opencode_parser.py`) extract messages, timestamps, and metadata.
3.  **Tagging & Summarization**: If configured, `OfflineTagGenerator` uses a local LLM to analyze the conversation content, generating relevant tags and a concise summary.
4.  **Syncing**: The `SyncEngine` writes markdown files to your Obsidian vault, updating only what has changed based on content hashing.

## Prerequisites

- **Python 3.9+**
- **Ollama** (optional but recommended for AI tagging)

## Install Claude Vault

```bash
# Clone or download the project
git clone https://github.com/thinkstylestudio/claude-vault.git
cd claude-vault

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
claude-vault --help
```

### Install Ollama (Optional for AI tagging & semantic search)

```bash
# On macOS
brew install ollama

# Start ollama
ollama serve

# Pull a balanced model for tagging (quality/speed)
ollama pull llama3.2:3b

# Pull embedding model for semantic search (optional)
ollama pull nomic-embed-text
```

## Quick Usage

### 1. Initialize Vault

```bash
# Navigate to your Obsidian vault
cd ~/Documents/ObsidianVault

# Initialize Claude Vault
claude-vault init
```

### 2. Sync Conversations

```bash
# Claude Web export
claude-vault sync ~/Downloads/conversations.json

# Claude Code history
claude-vault sync ~/.claude

# OpenCode (auto-detects .db file)
claude-vault sync ~/.local/share/opencode/opencode.db

# OpenCode (uses default path)
claude-vault sync --source opencode
```

### 3. Check Status

```bash
claude-vault status
```

## Supported Formats

All formats are automatically detected based on file extension, or you can specify with `--source`:

```bash
# Auto-detect format
claude-vault sync conversations.json
claude-vault sync code-history.jsonl
claude-vault sync ~/.claude
claude-vault sync ~/.local/share/opencode/opencode.db

# Explicit source
claude-vault sync export.json --source web
claude-vault sync export.jsonl --source code
claude-vault sync --source opencode
```

### OpenCode Details

OpenCode stores conversations in a SQLite database at `~/.local/share/opencode/opencode.db`. Claude Vault reads sessions, messages, and parts directly from this database.

- Only root sessions are imported (child/sub-sessions are skipped)
- Text, tool, and reasoning parts are included in the markdown output
- Tool outputs are truncated to 500 characters for readability
- Timestamps are converted from milliseconds to human-readable dates

## Common Commands

```bash
# Search conversations
claude-vault search "python"

# Search with tag filter
claude-vault search "API" --tag code

# Regenerate tags with AI
claude-vault retag

# Verify vault integrity
claude-vault verify

# Clean up orphaned entries
claude-vault verify --cleanup

# Preview changes before applying (dry-run mode)
claude-vault sync ~/Downloads/conversations.json --dry-run
claude-vault retag --dry-run
claude-vault verify --cleanup --dry-run
```

## Auto-Sync with Watch Mode

Keep your vault automatically synced with conversation changes:

```bash
# Add paths to watch
claude-vault watch-add ~/Downloads --source web
claude-vault watch-add ~/.claude --source code
claude-vault watch-add ~/.local/share/opencode/opencode.db --source opencode

# Start watching (stays in foreground with live updates)
claude-vault watch

# Or run in background
claude-vault watch &
```

### Watch Mode Commands

```bash
# Check watch status
claude-vault watch-status

# Stop watch mode
claude-vault watch-stop

# Remove a watch path
claude-vault watch-remove ~/Downloads
```

## Semantic Search

Find conversations by meaning, not just keywords:

```bash
# Install embedding model (first time only)
ollama pull nomic-embed-text

# Search semantically (default mode if Ollama is running)
claude-vault search "async programming"

# Semantic search (AI-powered, finds by concept)
claude-vault search "machine learning" --mode semantic

# Keyword search (traditional exact matching)
claude-vault search "python" --mode keyword

# Auto mode (uses semantic if available, falls back to keyword)
claude-vault search "debugging" --mode auto

# Adjust similarity threshold (0.0-1.0, default 0.5)
claude-vault search "API" --mode semantic --threshold 0.7
```

## Troubleshooting

**"Ollama not running":** Start with `ollama serve`. For semantic search, also run `ollama pull nomic-embed-text`

**"Module not found:"** Reinstall with `pip install -e .`

**"Not initialized:"** Run `claude-vault init` first

**"utf-8 codec can't decode":** See [documents/ENCODING_FIX.md](documents/ENCODING_FIX.md) for details on encoding handling.

## Configuration

Claude Vault supports global configuration for Ollama settings and custom keywords.

```bash
# View current configuration
claude-vault config
```

## CLI Commands

#### `init`

Initialize Claude Vault in the specified directory.

```bash
claude-vault init [VAULT_PATH]
```

#### `sync`

Sync conversations to markdown files.

```bash
claude-vault sync [EXPORT_PATH] [--source auto|web|code|opencode] [--dry-run]
```

**Examples:**
```bash
# Claude web export
claude-vault sync ~/Downloads/conversations.json

# Claude Code history
claude-vault sync ~/.claude

# OpenCode (auto-detects .db)
claude-vault sync ~/.local/share/opencode/opencode.db

# OpenCode (uses default path)
claude-vault sync --source opencode
```

#### `status`

Show Claude Vault status and statistics.

```bash
claude-vault status
```

#### `verify`

Verify integrity of tracked conversations and optionally clean up mismatches.

```bash
claude-vault verify
claude-vault verify --cleanup
```

#### `search`

Search across all conversations.

```bash
claude-vault search KEYWORD [--tag TAG] [--mode auto|semantic|keyword] [--threshold 0.5]
```

#### `retag`

Regenerate tags and summaries for conversations using AI.

```bash
claude-vault retag [--force] [--dry-run]
```

**Requirements:** Requires Ollama to be running with `llama3.2:3b` model installed.

#### `config`

Manage global configuration.

```bash
claude-vault config
```

#### `watch-add`

Add a path to the watch list.

```bash
claude-vault watch-add <path> [--source auto|web|code|opencode]
```

### Getting Help

```bash
claude-vault --help
claude-vault [COMMAND] --help
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up the development environment and submit pull requests.

## License

Claude Vault is available under a **dual-license model**:

### Open Source License (AGPL-3.0)

Free for personal use, open source projects, educational purposes, research, and non-commercial applications.

### Commercial License

Required for proprietary/closed-source applications, commercial SaaS products, and enterprise deployments. Contact via GitHub for pricing.

---

**Note:** By using, modifying, or distributing Claude Vault without obtaining a commercial license, you agree to comply with the AGPL-3.0 terms.
