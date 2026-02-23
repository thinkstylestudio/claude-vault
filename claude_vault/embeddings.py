"""Embedding generation for semantic search"""

from typing import Any, Dict, List, cast

import numpy as np
import requests

from claude_vault.config import load_config
from claude_vault.models import Conversation


class EmbeddingGenerator:
    """Generate embeddings using Ollama"""

    def __init__(self):
        self.config = load_config()
        self.ollama_url = self.config.embeddings.url
        self.model = self.config.embeddings.model

    def is_available(self) -> bool:
        """Check if Ollama embedding service is available"""
        try:
            base_url = self.ollama_url.rsplit("/api", 1)[0]
            response = requests.get(base_url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            response = requests.post(
                self.ollama_url,
                json={"model": self.model, "input": text},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                # Ollama returns embeddings as nested list [[...]]
                embeddings = data.get("embeddings", [[]])
                if embeddings and len(embeddings) > 0:
                    return cast(List[float], embeddings[0])

            return []

        except Exception as e:
            print(f"⚠️ Embedding generation failed: {e}")
            return []

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            emb = self.generate_embedding(text)
            embeddings.append(emb)
        return embeddings


class ConversationChunker:
    """Chunk conversations into segments for embedding"""

    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_conversation(self, conversation: Conversation) -> List[Dict[str, Any]]:
        """
        Chunk conversation into semantically meaningful segments

        Args:
            conversation: Conversation to chunk

        Returns:
            List of chunks with text and metadata
        """
        chunks: List[Dict[str, Any]] = []

        # Chunk by message pairs (human + assistant)
        for i in range(0, len(conversation.messages), 2):
            human_msg = (
                conversation.messages[i] if i < len(conversation.messages) else None
            )
            assistant_msg = (
                conversation.messages[i + 1]
                if i + 1 < len(conversation.messages)
                else None
            )

            # Build chunk text with context
            chunk_text = f"Title: {conversation.title}\n"
            if human_msg:
                chunk_text += f"Human: {human_msg.content[:1000]}\n"
            if assistant_msg:
                chunk_text += f"Assistant: {assistant_msg.content[:1000]}"

            # If chunk is too long, split it
            if len(chunk_text) > self.chunk_size:
                sub_chunks = self._split_long_text(chunk_text)
                for _idx, sub_chunk in enumerate(sub_chunks):
                    chunks.append(
                        {
                            "chunk_index": len(chunks),
                            "text": sub_chunk,
                            "message_indices": [i, i + 1] if assistant_msg else [i],
                        }
                    )
            else:
                chunks.append(
                    {
                        "chunk_index": len(chunks),
                        "text": chunk_text,
                        "message_indices": [i, i + 1] if assistant_msg else [i],
                    }
                )

        return chunks

    def _split_long_text(self, text: str) -> List[str]:
        """Split long text into chunks with overlap"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)

                if break_point > start + self.chunk_size // 2:
                    end = start + break_point + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())

            # Move to next chunk with overlap
            start = end - self.overlap if end < len(text) else end

        return chunks


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    if len(a) == 0 or len(b) == 0:
        return 0.0

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        return 0.0

    return float(np.dot(a, b) / (a_norm * b_norm))
