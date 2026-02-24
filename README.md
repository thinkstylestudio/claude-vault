# Claude Vault

Transform your Claude conversations into a searchable, organized knowledge base in Obsidian.

## What is Claude Vault?

Claude Vault is a command-line tool that syncs your Claude AI conversations into beautifully formatted Markdown files that integrate seamlessly with Obsidian and other note-taking tools.

## Features

- ✅ **Local-first**: Your conversations, your vault, your control
- ✅ **Simple CLI**: Easy to use, powerful features
- ✅ **Bulk Historical Import**: Import your entire Claude conversation history at once
- ✅ **Obsidian-native**: Full frontmatter, tags, and metadata support
- ✅ **AI-Powered Tagging & Summarization**: Automatic generation of tags and summaries using local LLMs (Ollama) - no API costs
- ✅ **Auto-Sync with Watch Mode**: Real-time syncing when conversation files change
- ✅ **Semantic Search**: AI-powered search by meaning, not just keywords
- ✅ **Bi-directional sync**: Rename and move files freely - they stay in sync
- ✅ **Smart updates**: Only syncs what's changed
- ✅ **UUID tracking**: Maintains file relationships even after renaming
- ✅ **Cross-Conversation Search**: Search across all conversations with context and navigate to related ones
- ✅ **Smart Relationship Detection**: Automatically finds and links related conversations via common tags

## Key Features of the Code Parser

The JSONL parser handles:
- ✅ **Session grouping** - Groups messages by `sessionId`
- ✅ **Tool results** - Shows before/after state for tools
- ✅ **Timestamps** - Preserves message timing
- ✅ **Summary as title** - Uses the summary line as conversation title
- ✅ **Code-specific tags** - Adds 'code-session' tag to differentiate from web chats

## How it Works

Claude Vault uses a modular architecture to handle different conversation formats:

1.  **Format Detection**: Automatically identifies if a file is a Web export (`.json`) or Code History (`.jsonl`).
2.  **Parsing**: specialized parsers (`messages.py` vs `code_parser.py`) extract messages, timestamps, and metadata.
3.  **Tagging & Summarization**: If configured, `OfflineTagGenerator` uses a local LLM to analyze the conversation content, generating relevant tags and a concise summary.
4.  **Syncing**: The `SyncEngine` writes markdown files to your Obsidian vault, updating only what has changed based on content hashing.


### Prerequisites

- **Python 3.8+**
- **Ollama** (optional but recommended for AI tagging)

### Install Claude Vault

```bash
# Clone or download the project
git clone https://github.com/MarioPadilla/claude-vault.git
cd claude-vault

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
claude-vault --help
```

### Test
```bash
python tests/test_parser.py
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

### 1. Export Your Claude Conversations

1. Go to [claude.ai](https://claude.ai)
2. Click profile → Settings
3. Export conversations (downloads `conversations.json`)

### 2. Initialize Vault

```bash
# Navigate to your Obsidian vault
cd ~/Documents/ObsidianVault

# Initialize Claude Vault
claude-vault init
```

### 3. Sync Conversations
```bash
# Import all conversations
claude-vault sync ~/Downloads/conversations.json
```

## Supported Formats

Claude Vault supports multiple Claude conversation sources:

- **Claude Web Conversations** (.json) - From claude.ai exports
- **Claude Code History** (.jsonl) - From Claude Code IDE integration

Both formats are automatically detected based on file extension, or you can specify with `--source`:

```bash
# Auto-detect format
claude-vault sync conversations.json
claude-vault sync code-history.jsonl
# Sync from entire .claude folder
claude-vault sync ~/.claude

# Explicit source
claude-vault sync export.json --source web
claude-vault sync export.jsonl --source code
```

### 4. Check Status

```bash
claude-vault status
```

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

## Dry-Run Mode

Preview changes before applying them to your vault:

```bash
# Preview what would be synced
claude-vault sync conversations.json --dry-run

# Preview tag regeneration
claude-vault retag --dry-run
claude-vault retag --force --dry-run

# Preview cleanup operations
claude-vault verify --cleanup --dry-run
```

Dry-run mode shows:

- Summary statistics of changes
- Detailed preview of affected files
- No actual modifications to files or database
- Progress indicators for all operations

## Auto-Sync with Watch Mode

Keep your vault automatically synced with Claude conversations in real-time:

### Setup Watch Mode

```bash
# Add paths to watch
claude-vault watch-add ~/Downloads --source web
claude-vault watch-add ~/.claude --source code

# Start watching (stays in foreground with live updates)
claude-vault watch

# Or run in background
claude-vault watch &
```

Watch mode detects file changes in real-time and syncs automatically. No more manual sync commands!

### Watch Mode Commands

```bash
# Check watch status
claude-vault watch-status

# Stop watch mode
claude-vault watch-stop

# Remove a watch path
claude-vault watch-remove ~/Downloads
```

### How It Works

- **Debouncing**: Waits 2 seconds after file changes to handle editor auto-saves
- **Throttling**: Prevents excessive syncs (minimum 10 seconds between syncs per file)
- **Smart Detection**: Automatically detects Web (.json) vs Code (.jsonl) formats
- **Error Handling**: Continues watching even if individual syncs fail

## Semantic Search

Find conversations by meaning, not just keywords:

### Setup Semantic Search

```bash
# Install embedding model (first time only)
ollama pull nomic-embed-text

# Search semantically (default mode if Ollama is running)
claude-vault search "async programming"
```

Semantic search understands concepts - searching "asynchronous programming" will find conversations about "asyncio" even without exact keyword matches!

### Search Modes

```bash
# Semantic search (AI-powered, finds by concept)
claude-vault search "machine learning" --mode semantic

# Keyword search (traditional exact matching)
claude-vault search "python" --mode keyword

# Auto mode (uses semantic if available, falls back to keyword)
claude-vault search "debugging" --mode auto

# Adjust similarity threshold (0.0-1.0, default 0.5)
claude-vault search "API" --mode semantic --threshold 0.7
```

### How It Works

1. **First Search**: Automatically generates embeddings for all conversations (one-time process)
2. **Subsequent Searches**: Instant semantic search using cached embeddings
3. **Relevance Scores**: Each result shows similarity score (0.0-1.0)
4. **Smart Chunking**: Long conversations split into chunks for better accuracy
5. **Offline-First**: All processing happens locally via Ollama (no external APIs)

### Search Features

- **Conceptual Matching**: Finds related topics even with different terminology
- **Context Preview**: Shows relevant snippets from matching conversations
- **Relevance Ranking**: Results sorted by similarity score
- **Hybrid Search**: Combine semantic understanding with keyword precision
- **Fallback Support**: Auto-switches to keyword search if Ollama unavailable

## Troubleshooting

**"Ollama not running":** Start with `ollama serve`. For semantic search, also run `ollama pull nomic-embed-text`

**"Module not found:"** Reinstall with `pip install -e .`

**"Not initialized:"** Run `claude-vault init` first

## Configuration

Claude Vault supports global configuration for Ollama settings and custom keywords.

```bash
# View current configuration
claude-vault config
```

The config is stored in `~/.claude-vault/config.json`. You can customize:
- **Ollama Model**: Change the model used for tagging (default: `llama3.2:3b`)
- **Ollama URL**: Change the Ollama API endpoint
- **Custom Keywords**: Add your own keywords for fallback tagging

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up the development environment and submit pull requests.

## License

Claude Vault is available under a **dual-license model**:

### 🆓 Open Source License (AGPL-3.0)

**Free for:**
- ✅ Personal use
- ✅ Open source projects
- ✅ Educational purposes
- ✅ Research and academic use
- ✅ Non-commercial applications

**Requirements under AGPL-3.0:**
- Must disclose source code of any modifications
- Must keep the same license (AGPL-3.0)
- Must provide source code to users (including SaaS/network users)
- Any derivative work must also be licensed under AGPL-3.0

**Perfect for:** Developers, hobbyists, students, and open-source contributors who want to freely use and modify Claude Vault.

---

### 💼 Commercial License

**Required for:**
- ❌ Proprietary/closed-source applications
- ❌ Commercial SaaS products
- ❌ Enterprise deployments where source code disclosure is not desired
- ❌ Products that cannot comply with AGPL-3.0 copyleft terms

**Benefits of Commercial License:**
- ✅ Use Claude Vault in proprietary applications
- ✅ No obligation to disclose your source code
- ✅ Freedom from AGPL-3.0 copyleft requirements
- ✅ Priority support (optional)
- ✅ Custom modifications and consulting (optional)

**Pricing:** Contact me for a quote based on your use case.

📧 **Contact:** Github
📝 **Subject:** Claude Vault Commercial License Inquiry

---

### ❓ Which License Do I Need?

| Use Case | License Needed |
|----------|---------------|
| Building an open-source tool | AGPL-3.0 (Free) ✅ |
| Learning/experimenting | AGPL-3.0 (Free) ✅ |
| Contributing to Claude Vault | AGPL-3.0 (Free) ✅ |
| Internal company tool (source shared with employees) | AGPL-3.0 (Free) ✅ |
| Commercial SaaS product | Commercial 💼 |
| Closed-source application | Commercial 💼 |
| Selling a product that includes Claude Vault | Commercial 💼 |
| Enterprise deployment (no source disclosure) | Commercial 💼 |

**Still unsure?** Contact me

---

**Note:** By using, modifying, or distributing Claude Vault without obtaining a commercial license, you agree to comply with the AGPL-3.0 terms.

### CLI Commands

#### `init`

Initialize Claude Vault in the specified directory.

```bash
claude-vault init [VAULT_PATH]
```

**Example:**
```bash
claude-vault init
claude-vault init ~/Documents/my-vault
```

#### `sync`

Sync Claude conversations to markdown files.

```bash
claude-vault sync [EXPORT_PATH]
```

**Examples:**
```bash
claude-vault sync ~/Downloads/conversations.json
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
```

**Examples:**
```bash
claude-vault verify
claude-vault verify --cleanup
```

#### `search`

Search across all conversations.

```bash
claude-vault search KEYWORD [OPTIONS]
```
**Arguments:**
- `KEYWORD` - Search term **(required)**

**Options:**
- `--tag TEXT` - Filter by tag
- `--show-related / --no-show-related` - Show related conversations (default: enabled)

**Examples:**
```bash
# Basic search
claude-vault search "python"

# Search with tag filter
claude-vault search "machine learning" --tag "ai"

# Search without showing related conversations
claude-vault search "debugging" --no-show-related
```

#### `retag`

Regenerate tags and summaries for conversations using AI.

```bash
claude-vault retag [OPTIONS]
```

**Options:**
- `--force` - Regenerate all tags, even existing ones

**Examples:**
```bash
# Tag conversations without tags
claude-vault retag

# Force regenerate all tags
claude-vault retag --force
```

**Requirements:** Requires Ollama to be running with `llama3.2:3b` model installed.

### Getting Help

Get help for any command:

```bash
claude-vault --help
claude-vault [COMMAND] --help
```

**Examples:**
```bash
claude-vault sync --help
claude-vault search --help
```
