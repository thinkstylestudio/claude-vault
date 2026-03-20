# Encoding Fix for OpenCode Parser

## Problem

When syncing OpenCode conversations, users encountered a UTF-8 decode error:

```
Error during sync: 'utf-8' codec can't decode byte 0xb5 in position 27: invalid start byte
```

This error occurred when processing tool outputs from web search and web fetch operations, which can contain binary data or non-UTF-8 characters.

## Root Cause

OpenCode stores tool outputs as strings in SQLite's `data` column. Some tool outputs (especially from web scraping) contain:

- Binary data (e.g., images, compressed content)
- Non-UTF-8 encoded text (e.g., Latin-1 characters)
- Mixed encodings from different sources

When the parser tried to process these outputs, the string operations failed because Python's string handling expects valid UTF-8.

## Solution

Added defensive encoding handling at multiple layers:

### 1. Parser Layer (`opencode_parser.py`)

```python
# Convert bytes to string with replacement
if isinstance(text, bytes):
    text = text.decode("utf-8", errors="replace")

# Sanitize content before returning
content = content.encode("utf-8", errors="replace").decode("utf-8")
```

### 2. Sync Layer (`sync.py`)

```python
# Safe content hash generation
try:
    current_hash = conv.content_hash()
except UnicodeDecodeError as e:
    # Sanitize message content and retry
    for msg in conv.messages:
        if isinstance(msg.content, bytes):
            msg.content = msg.content.decode("utf-8", errors="replace")
    current_hash = conv.content_hash()
```

### 3. Error Handling

- JSON parsing errors are caught and logged as warnings
- Individual part failures don't stop the entire sync
- Encoding issues are sanitized rather than causing failures

## Testing

- All 76 tests pass
- Tested with real OpenCode database containing web search results
- Verified encoding handling for bytes, strings, and mixed types

## Impact

- **Backward compatible**: No changes to existing functionality
- **Graceful degradation**: Problematic content is sanitized, not lost
- **User-friendly**: Clear warning messages for encoding issues

## Related Files

- `claude_vault/opencode_parser.py` — Parser encoding handling
- `claude_vault/sync.py` — Sync engine encoding safety
- `tests/test_opencode_parser.py` — Parser unit tests
