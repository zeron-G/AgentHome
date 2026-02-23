"""RAG (Retrieval-Augmented Generation) storage module.

Swap the storage backend by replacing JSONRAGStorage with any class that
implements BaseRAGStorage — e.g. ChromaDB, SQLite, or a remote vector store.
"""
from rag.base import BaseRAGStorage
from rag.json_storage import JSONRAGStorage
from rag.records import MemoryRecord

__all__ = ["BaseRAGStorage", "JSONRAGStorage", "MemoryRecord"]
