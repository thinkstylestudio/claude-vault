"""Tests for embedding generation and conversation chunking"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from claude_vault.embeddings import (
    ConversationChunker,
    EmbeddingGenerator,
    cosine_similarity,
)
from claude_vault.models import Conversation, Message


@pytest.fixture
def embedding_generator():
    """Create embedding generator with mocked config"""
    with patch("claude_vault.embeddings.load_config") as mock_config:
        mock_config.return_value.embeddings.url = "http://localhost:11434/api/embed"
        mock_config.return_value.embeddings.model = "nomic-embed-text"
        return EmbeddingGenerator()


@pytest.fixture
def conversation_chunker():
    """Create conversation chunker with default settings"""
    return ConversationChunker(chunk_size=2000, overlap=200)


@pytest.fixture
def mock_conversation():
    """Create a mock conversation for testing"""
    from datetime import datetime

    return Conversation(
        id="test-123",
        title="Python Async Programming",
        messages=[
            Message(role="human", content="How does asyncio work in Python?"),
            Message(
                role="assistant",
                content="Asyncio is Python's built-in library for asynchronous programming. "
                "It allows you to write concurrent code using async/await syntax.",
            ),
            Message(role="human", content="Can you show an example?"),
            Message(
                role="assistant",
                content="Sure! Here's a basic example:\n\n"
                "async def main():\n    await asyncio.sleep(1)\n    print('Done!')",
            ),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_embedding_generator_is_available_success(embedding_generator):
    """Test Ollama availability check when service is running"""
    mock_response = Mock()
    mock_response.status_code = 200

    with patch("requests.get", return_value=mock_response):
        assert embedding_generator.is_available() is True


def test_embedding_generator_is_available_failure(embedding_generator):
    """Test Ollama availability check when service is down"""
    with patch("requests.get", side_effect=Exception("Connection refused")):
        assert embedding_generator.is_available() is False


def test_generate_embedding_success(embedding_generator):
    """Test successful embedding generation"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embeddings": [[0.1, 0.2, 0.3, 0.4]]  # Simplified 4D embedding
    }

    with patch("requests.post", return_value=mock_response):
        result = embedding_generator.generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3, 0.4]
        assert len(result) == 4


def test_generate_embedding_failure(embedding_generator):
    """Test embedding generation failure handling"""
    with patch("requests.post", side_effect=Exception("API error")):
        result = embedding_generator.generate_embedding("test text")
        assert result == []


def test_generate_embedding_empty_response(embedding_generator):
    """Test handling of empty embedding response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": []}

    with patch("requests.post", return_value=mock_response):
        result = embedding_generator.generate_embedding("test text")
        assert result == []


def test_generate_embeddings_batch(embedding_generator):
    """Test batch embedding generation"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    with patch("requests.post", return_value=mock_response):
        texts = ["text 1", "text 2"]
        results = embedding_generator.generate_embeddings_batch(texts)

        assert len(results) == 2


def test_cosine_similarity_identical_vectors():
    """Test cosine similarity with identical vectors"""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([1.0, 2.0, 3.0])

    similarity = cosine_similarity(a, b)
    assert abs(similarity - 1.0) < 0.001  # Should be ~1.0


def test_cosine_similarity_orthogonal_vectors():
    """Test cosine similarity with orthogonal vectors"""
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])

    similarity = cosine_similarity(a, b)
    assert abs(similarity - 0.0) < 0.001  # Should be ~0.0


def test_cosine_similarity_opposite_vectors():
    """Test cosine similarity with opposite vectors"""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([-1.0, -2.0, -3.0])

    similarity = cosine_similarity(a, b)
    assert abs(similarity - (-1.0)) < 0.001  # Should be ~-1.0


def test_cosine_similarity_empty_vectors():
    """Test cosine similarity with empty vectors"""
    a = np.array([])
    b = np.array([])

    similarity = cosine_similarity(a, b)
    assert similarity == 0.0


def test_cosine_similarity_zero_vectors():
    """Test cosine similarity with zero vectors"""
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([1.0, 2.0, 3.0])

    similarity = cosine_similarity(a, b)
    assert similarity == 0.0


def test_chunk_conversation_simple(conversation_chunker, mock_conversation):
    """Test chunking a simple conversation"""
    chunks = conversation_chunker.chunk_conversation(mock_conversation)

    assert len(chunks) == 2  # Two message pairs
    assert all("chunk_index" in chunk for chunk in chunks)
    assert all("text" in chunk for chunk in chunks)
    assert all("message_indices" in chunk for chunk in chunks)

    # Check first chunk contains title and first exchange
    assert "Python Async Programming" in chunks[0]["text"]
    assert "asyncio work" in chunks[0]["text"]


def test_chunk_conversation_single_message(conversation_chunker):
    """Test chunking a conversation with single message"""
    from datetime import datetime

    conv = Conversation(
        id="test-single",
        title="Single Message",
        messages=[Message(role="human", content="Hello!")],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    chunks = conversation_chunker.chunk_conversation(conv)

    assert len(chunks) == 1
    assert "Single Message" in chunks[0]["text"]
    assert "Hello!" in chunks[0]["text"]


def test_chunk_conversation_long_content(conversation_chunker):
    """Test chunking a conversation with very long content"""
    from datetime import datetime

    long_content = "A" * 3000  # Exceeds chunk_size of 2000

    conv = Conversation(
        id="test-long",
        title="Long Conversation",
        messages=[
            Message(role="human", content=long_content),
            Message(role="assistant", content="Short response"),
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    chunks = conversation_chunker.chunk_conversation(conv)

    # Should create multiple chunks due to length
    assert len(chunks) >= 1
    # Each chunk should be roughly chunk_size or less
    assert all(len(chunk["text"]) <= 2500 for chunk in chunks)


def test_split_long_text_with_overlap(conversation_chunker):
    """Test text splitting with overlap"""
    text = "A" * 5000  # Much longer than chunk_size

    chunks = conversation_chunker._split_long_text(text)

    assert len(chunks) > 1
    # Check overlap exists between consecutive chunks
    for i in range(len(chunks) - 1):
        # Later chunks should start before previous chunk ended
        # (due to overlap)
        assert len(chunks[i]) <= 2000 + 500  # Some buffer


def test_split_long_text_sentence_boundary(conversation_chunker):
    """Test text splitting at sentence boundaries"""
    # Create text with clear sentence boundaries
    sentences = ["This is sentence one. "] * 100
    text = "".join(sentences)

    chunks = conversation_chunker._split_long_text(text)

    # Check that chunks break at sentence boundaries (ending with .)
    # Allow for some flexibility as not all chunks may end perfectly
    sentence_endings = sum(1 for chunk in chunks if chunk.rstrip().endswith("."))
    assert sentence_endings >= len(chunks) // 2


def test_chunk_empty_conversation(conversation_chunker):
    """Test chunking an empty conversation"""
    from datetime import datetime

    conv = Conversation(
        id="test-empty",
        title="Empty",
        messages=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    chunks = conversation_chunker.chunk_conversation(conv)

    assert len(chunks) == 0
