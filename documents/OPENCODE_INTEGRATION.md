# OpenCode Integration Planning

## Overview

This document outlines the planning and implementation of OpenCode support in Claude Vault, allowing users to sync their OpenCode conversations to Obsidian.

## Background

OpenCode is an open-source AI coding agent that stores conversation history in a SQLite database (`opencode.db`). Unlike Claude's web export (JSON) and Claude Code (JSONL) formats, OpenCode uses a structured database with separate tables for projects, sessions, messages, and parts.

## Decision: SQLite Only

We chose to support only the SQLite format (not legacy JSON or export command output) because:

1. **Universal coverage**: All OpenCode users on v1.2.0+ (February 2026) have the SQLite format
2. **Simplicity**: Single source of truth, no format detection complexity
3. **Performance**: Direct database queries are faster than parsing JSON files
4. **Maintainability**: One code path to maintain instead of multiple formats

## OpenCode Database Schema

### Tables

```sql
project (id, worktree, name, time_created, time_updated)
session (id, project_id, parent_id, title, directory, time_created, time_updated)
message (id, session_id, time_created, data)
part (id, message_id, session_id, time_created, data)
```

### Key Observations

- **Sessions** can have parent-child relationships (parent_id)
- **Messages** store role and metadata in a JSON `data` column
- **Parts** store content (text, tool output, reasoning) in a JSON `data` column
- **Timestamps** are Unix epoch in milliseconds
- **Tool outputs** can contain binary data or non-UTF-8 characters

## Implementation Approach

### Parser Design

The `OpenCodeParser` class follows the same interface as existing parsers:

```python
class OpenCodeParser:
    def parse(self, db_path: Path) -> List[Conversation]:
        # 1. Connect to SQLite database (read-only)
        # 2. Query root sessions (parent_id IS NULL)
        # 3. For each session, query messages
        # 4. For each message, query parts and extract content
        # 5. Build Conversation objects
```

### Content Extraction

Parts are processed based on their type:

| Part Type | Handling |
|-----------|----------|
| `text` | Extract `text` field directly |
| `tool` | Format as code block with tool name, input, and output |
| `reasoning` | Format as labeled section |
| Other | Skip (step-start, step-finish, patch, file, etc.) |

### Auto-Detection

The CLI detects OpenCode format when:
- File has `.db` extension
- File is named `opencode.db`
- User specifies `--source opencode`

### Default Path

When `--source opencode` is used without a path, the default location is:
```
~/.local/share/opencode/opencode.db
```

## Testing Strategy

### Unit Tests

- Synthetic SQLite database with known data
- Test session parsing, message extraction, part handling
- Test edge cases (empty DB, missing file, child sessions)
- Test timestamp conversion (milliseconds to datetime)

### Integration Tests

- CLI auto-detection
- Default path resolution
- Dry-run mode

### Test Coverage

13 parser tests + 2 CLI tests = 15 total

## Open Questions

1. **Child sessions**: Should we support importing child/sub-sessions as separate conversations?
   - Decision: Skip for now, only import root sessions
   
2. **Tool output truncation**: What's the right limit for tool output size?
   - Decision: 500 characters (matches existing code parser behavior)

3. **Project grouping**: Should conversations from the same project be linked?
   - Decision: Use project name as a tag (e.g., `project:my-project`)

## Future Enhancements

- [ ] Support for importing child sessions with context
- [ ] Filtering by project
- [ ] Support for OpenCode's export command output format
- [ ] Metadata from session summaries (additions, deletions, files changed)
