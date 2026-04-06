from __future__ import annotations

import hashlib

import numpy as np


class SimpleHashEmbedder:
	"""Deterministic lightweight embedder used when no model backend is configured."""

	def __init__(self, dim: int = 384):
		self.dim = int(dim)

	def encode(self, text: str) -> np.ndarray:
		vec = np.zeros(self.dim, dtype=np.float32)
		if not text:
			return vec

		# Hash each token into a stable bucket and accumulate counts.
		for token in text.lower().split():
			idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
			vec[idx] += 1.0

		norm = float(np.linalg.norm(vec))
		if norm > 0:
			vec /= norm
		return vec


def get_embedder() -> SimpleHashEmbedder:
	return SimpleHashEmbedder()
