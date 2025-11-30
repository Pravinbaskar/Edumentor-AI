from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("edumentor.vector_store")


class VectorStore:
    """FAISS-based vector store for subject-specific document retrieval."""

    def __init__(self, data_dir: str = "data/vector_store"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        
        # Store indexes and metadata per subject
        self.indexes: Dict[str, faiss.IndexFlatL2] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
        
        self._load_all_indexes()

    def _get_index_path(self, subject: str) -> Path:
        """Get path for subject-specific FAISS index."""
        return self.data_dir / f"{subject}_index.faiss"

    def _get_metadata_path(self, subject: str) -> Path:
        """Get path for subject-specific metadata."""
        return self.data_dir / f"{subject}_metadata.json"

    def _load_all_indexes(self):
        """Load all existing indexes and metadata from disk."""
        for subject in ["maths", "science", "evs"]:
            index_path = self._get_index_path(subject)
            metadata_path = self._get_metadata_path(subject)
            
            if index_path.exists() and metadata_path.exists():
                try:
                    # Load FAISS index
                    self.indexes[subject] = faiss.read_index(str(index_path))
                    
                    # Load metadata
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata[subject] = json.load(f)
                    
                    logger.info(f"Loaded index for {subject}: {len(self.metadata[subject])} documents")
                except Exception as e:
                    logger.error(f"Failed to load index for {subject}: {e}")
                    self._init_subject_index(subject)
            else:
                self._init_subject_index(subject)

    def _init_subject_index(self, subject: str):
        """Initialize a new empty index for a subject."""
        self.indexes[subject] = faiss.IndexFlatL2(self.embedding_dim)
        self.metadata[subject] = []
        logger.info(f"Initialized new index for {subject}")

    def _save_index(self, subject: str):
        """Save index and metadata to disk."""
        try:
            index_path = self._get_index_path(subject)
            metadata_path = self._get_metadata_path(subject)
            
            # Save FAISS index
            faiss.write_index(self.indexes[subject], str(index_path))
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata[subject], f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved index for {subject}")
        except Exception as e:
            logger.error(f"Failed to save index for {subject}: {e}")

    def add_documents(
        self,
        subject: str,
        texts: List[str],
        source: str,
        chunk_size: int = 500
    ) -> int:
        """
        Add documents to the vector store for a specific subject.
        
        Args:
            subject: Subject name (maths, science, evs)
            texts: List of text chunks to add
            source: Source identifier (e.g., filename)
            chunk_size: Maximum chunk size for splitting
            
        Returns:
            Number of chunks added
        """
        if subject not in self.indexes:
            self._init_subject_index(subject)
        
        if not texts:
            return 0
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to FAISS index
        start_idx = len(self.metadata[subject])
        self.indexes[subject].add(embeddings)
        
        # Store metadata
        for i, text in enumerate(texts):
            self.metadata[subject].append({
                "text": text,
                "source": source,
                "index": start_idx + i
            })
        
        # Save to disk
        self._save_index(subject)
        
        logger.info(f"Added {len(texts)} chunks to {subject} from {source}")
        return len(texts)

    def search(
        self,
        subject: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in a subject's vector store.
        
        Args:
            subject: Subject name to search in
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of dicts with 'text', 'source', and 'score' keys
        """
        if subject not in self.indexes or len(self.metadata[subject]) == 0:
            logger.info(f"No documents in {subject} index")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search in FAISS
        k = min(top_k, len(self.metadata[subject]))
        distances, indices = self.indexes[subject].search(query_embedding, k)
        
        # Collect results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata[subject]):
                meta = self.metadata[subject][idx]
                results.append({
                    "text": meta["text"],
                    "source": meta["source"],
                    "score": float(dist),
                    "rank": i + 1
                })
        
        return results

    def get_subject_stats(self, subject: str) -> Dict[str, Any]:
        """Get statistics for a subject's vector store."""
        if subject not in self.indexes:
            return {"document_count": 0, "sources": []}
        
        sources = list(set(meta["source"] for meta in self.metadata[subject]))
        return {
            "document_count": len(self.metadata[subject]),
            "sources": sources
        }

    def delete_subject_data(self, subject: str):
        """Delete all data for a subject."""
        if subject in self.indexes:
            # Remove from memory
            del self.indexes[subject]
            del self.metadata[subject]
            
            # Remove from disk
            index_path = self._get_index_path(subject)
            metadata_path = self._get_metadata_path(subject)
            
            if index_path.exists():
                index_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            # Reinitialize
            self._init_subject_index(subject)
            logger.info(f"Deleted all data for {subject}")
