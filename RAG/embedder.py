from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbedder:
	"""Pretrained SentenceTransformer embedder using all-MiniLM-L6-v2 model."""

	def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
		"""
		Initialize the embedder with a pretrained model.
		
		Args:
			model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
				- 22MB, 384-dim, very fast, no GPU needed
		"""
		print(f"[Embedder] Loading model: {model_name}...", flush=True)
		self.model = SentenceTransformer(model_name)
		print(f"[Embedder] Model loaded. Dimension: {self.model.get_sentence_embedding_dimension()}", flush=True)

	def encode(self, text: str) -> np.ndarray:
		"""
		Encode text to embedding vector using pretrained neural model.
		
		Args:
			text: Input text to embed
			
		Returns:
			384-dimensional embedding vector as numpy array
		"""
		if not text:
			return np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
		
		# Use pretrained model to encode (semantic understanding, not hashing)
		embedding = self.model.encode(text, convert_to_numpy=True)
		return embedding


def get_embedder() -> SentenceTransformerEmbedder:
	return SentenceTransformerEmbedder()
