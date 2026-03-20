"""Tests for semantic search engine"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import frontmatter
import numpy as np
import pytest

from claude_vault.semantic_search import SearchResult, SemanticSearchEngine


@pytest.fixture
def temp_vault():
    """Create a temporary vault directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        conversations_dir = vault_path / "conversations"
        conversations_dir.mkdir()

        # Create test conversation files
        conv1 = frontmatter.Post(
            content="## 👤 You\n\nHow does async work?\n\n---\n\n## 🤖 Claude\n\nAsync programming uses asyncio in Python.",
            uuid="test-123",
            title="Python Async",
            tags=["python", "async"],
            date="2024-01-01",
        )
        frontmatter.dump(conv1, conversations_dir / "python-async.md")

        conv2 = frontmatter.Post(
            content="## 👤 You\n\nExplain Flask routing\n\n---\n\n## 🤖 Claude\n\nFlask uses decorators for routing.",
            uuid="test-456",
            title="Flask Basics",
            tags=["python", "web"],
            date="2024-01-02",
        )
        frontmatter.dump(conv2, conversations_dir / "flask-basics.md")

        yield vault_path


@pytest.fixture
def search_engine(temp_vault):
    """Create semantic search engine with temp vault"""
    with patch("claude_vault.semantic_search.StateManager") as mock_state_class:
        mock_state = Mock()
        mock_state_class.return_value = mock_state

        # Mock the state methods
        mock_state.get_all_embeddings.return_value = []

        engine = SemanticSearchEngine(temp_vault)
        engine.state = mock_state

        yield engine


def test_is_available_when_ollama_running(search_engine):
    """Test availability check when Ollama is running"""
    with patch.object(search_engine.generator, "is_available", return_value=True):
        assert search_engine.is_available() is True


def test_is_available_when_ollama_down(search_engine):
    """Test availability check when Ollama is down"""
    with patch.object(search_engine.generator, "is_available", return_value=False):
        assert search_engine.is_available() is False


def test_search_ollama_unavailable(search_engine):
    """Test search when Ollama is not available"""
    with patch.object(search_engine, "is_available", return_value=False):
        results = search_engine.search("test query")

        assert results == []


def test_search_no_embeddings(search_engine):
    """Test search when no embeddings exist"""
    with patch.object(search_engine, "is_available", return_value=True):
        with patch.object(
            search_engine.generator, "generate_embedding", return_value=[0.1, 0.2, 0.3]
        ):
            search_engine.state.get_all_embeddings.return_value = []

            results = search_engine.search("test query")

            assert results == []


def test_search_success(search_engine, temp_vault):
    """Test successful semantic search"""
    # Mock query embedding
    query_embedding = np.array([0.5, 0.5, 0.5], dtype=np.float32)

    # Mock stored embeddings (similar to query)
    search_engine.state.get_all_embeddings.return_value = [
        {
            "conversation_uuid": "test-123",
            "chunk_index": 0,
            "chunk_text": "Python async programming",
            "embedding": np.array([0.6, 0.4, 0.5], dtype=np.float32),
            "file_path": str(temp_vault / "conversations" / "python-async.md"),
            "metadata": {},
        },
        {
            "conversation_uuid": "test-456",
            "chunk_index": 0,
            "chunk_text": "Flask web framework",
            "embedding": np.array([0.1, 0.1, 0.1], dtype=np.float32),
            "file_path": str(temp_vault / "conversations" / "flask-basics.md"),
            "metadata": {},
        },
    ]

    with patch.object(search_engine, "is_available", return_value=True):
        with patch.object(
            search_engine.generator,
            "generate_embedding",
            return_value=query_embedding.tolist(),
        ):
            results = search_engine.search("async programming", limit=10, threshold=0.5)

            assert len(results) >= 1
            assert all(isinstance(r, SearchResult) for r in results)
            assert results[0].score >= 0.5
            # Results should be sorted by score (descending)
            assert all(
                results[i].score >= results[i + 1].score
                for i in range(len(results) - 1)
            )


def test_search_threshold_filtering(search_engine, temp_vault):
    """Test that threshold filters low-similarity results"""
    query_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    # One high similarity, one low similarity
    search_engine.state.get_all_embeddings.return_value = [
        {
            "conversation_uuid": "test-123",
            "chunk_index": 0,
            "chunk_text": "High similarity",
            "embedding": np.array([0.9, 0.1, 0.0], dtype=np.float32),
            "file_path": str(temp_vault / "conversations" / "python-async.md"),
            "metadata": {},
        },
        {
            "conversation_uuid": "test-456",
            "chunk_index": 0,
            "chunk_text": "Low similarity",
            "embedding": np.array([0.0, 0.0, 1.0], dtype=np.float32),
            "file_path": str(temp_vault / "conversations" / "flask-basics.md"),
            "metadata": {},
        },
    ]

    with patch.object(search_engine, "is_available", return_value=True):
        with patch.object(
            search_engine.generator,
            "generate_embedding",
            return_value=query_embedding.tolist(),
        ):
            results = search_engine.search("test", threshold=0.7)

            # Only high-similarity result should pass threshold
            assert len(results) == 1
            assert results[0].conversation_uuid == "test-123"


def test_search_limit(search_engine, temp_vault):
    """Test that limit parameter works"""
    query_embedding = np.array([0.5, 0.5, 0.5], dtype=np.float32)

    # Create 5 similar embeddings
    embeddings = []
    for i in range(5):
        embeddings.append(
            {
                "conversation_uuid": f"test-{i}",
                "chunk_index": 0,
                "chunk_text": f"Content {i}",
                "embedding": np.array([0.5, 0.5, 0.5], dtype=np.float32),
                "file_path": str(temp_vault / "conversations" / f"conv-{i}.md"),
                "metadata": {},
            }
        )

    search_engine.state.get_all_embeddings.return_value = embeddings

    with patch.object(search_engine, "is_available", return_value=True):
        with patch.object(
            search_engine.generator,
            "generate_embedding",
            return_value=query_embedding.tolist(),
        ):
            results = search_engine.search("test", limit=3, threshold=0.5)

            assert len(results) <= 3


def test_search_result_structure(search_engine, temp_vault):
    """Test that search results have correct structure"""
    query_embedding = np.array([0.5, 0.5, 0.5], dtype=np.float32)

    search_engine.state.get_all_embeddings.return_value = [
        {
            "conversation_uuid": "test-123",
            "chunk_index": 0,
            "chunk_text": "Test content",
            "embedding": np.array([0.5, 0.5, 0.5], dtype=np.float32),
            "file_path": str(temp_vault / "conversations" / "python-async.md"),
            "metadata": {"test": "data"},
        }
    ]

    with patch.object(search_engine, "is_available", return_value=True):
        with patch.object(
            search_engine.generator,
            "generate_embedding",
            return_value=query_embedding.tolist(),
        ):
            results = search_engine.search("test", threshold=0.5)

            assert len(results) == 1
            result = results[0]

            assert result.conversation_uuid == "test-123"
            assert result.title == "Python Async"
            assert isinstance(result.tags, list)
            assert result.score >= 0.0 and result.score <= 1.0
            assert result.rank == 1
            assert result.chunk_text == "Test content"


def test_ensure_embeddings_exist_all_present(search_engine, temp_vault):
    """Test ensure_embeddings when all exist"""
    # Mock that all files have embeddings (by file path)
    search_engine.state.get_all_embeddings.return_value = [
        {"file_path": str(temp_vault / "conversations" / "python-async.md")},
        {"file_path": str(temp_vault / "conversations" / "flask-basics.md")},
    ]

    with patch("claude_vault.semantic_search.console") as mock_console:
        search_engine.ensure_embeddings_exist()

        # Should print success message
        mock_console.print.assert_called_once()
        assert "All files have embeddings" in str(mock_console.print.call_args)


def test_ensure_embeddings_exist_generates_missing(search_engine, temp_vault):
    """Test ensure_embeddings generates for missing files"""
    # Mock that one file has embeddings (python-async.md)
    search_engine.state.get_all_embeddings.return_value = [
        {"file_path": str(temp_vault / "conversations" / "python-async.md")},
    ]

    with patch.object(search_engine, "_generate_embeddings_for_file") as mock_generate:
        search_engine.ensure_embeddings_exist()

        # Should generate embeddings for flask-basics.md only
        assert mock_generate.call_count >= 1


def test_generate_embeddings_for_file(search_engine, tmp_path):
    """Test embedding generation for a single file"""
    # Create a test markdown file
    md_file = tmp_path / "test-conversation.md"
    post = frontmatter.Post(
        content="## 👤 You\n\nTest question\n\n---\n\n## 🤖 Claude\n\nTest answer",
        uuid="test-123",
        title="Test Conversation",
        tags=["test"],
        date="2024-01-01",
    )
    md_file.write_text(frontmatter.dumps(post))

    mock_embedding = [0.1, 0.2, 0.3]

    with patch.object(
        search_engine.generator, "generate_embedding", return_value=mock_embedding
    ):
        search_engine._generate_embeddings_for_file(md_file)

        # Should save embeddings
        assert search_engine.state.save_embedding.called
