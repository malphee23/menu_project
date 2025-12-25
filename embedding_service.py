import asyncio
import json
import os
from threading import Lock
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from database import db


class DishVectorStore:
    def __init__(
        self,
        index_path: str = "data/dish_index.faiss",
        metadata_path: str = "data/dish_metadata.json",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict] = []
        self.lock = Lock()
        self.vector_size = 384  # for all-MiniLM-L6-v2
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        self._load_index()

    def _load_model(self) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        return self.model

    def _load_index(self) -> None:
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexFlatIP(self.vector_size)
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def _save_index(self) -> None:
        if self.index is None:
            return
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def _fetch_dishes_with_tags(self) -> List[Dict]:
        with db.engine.connect() as conn:
            if not self._table_exists(conn, "dishes"):
                return []
            tags_exist = self._table_exists(conn, "dish_tag_map") and self._table_exists(
                conn, "dish_tags"
            )
            if tags_exist:
                query = """
                    SELECT d.id, d.name, d.description,
                           COALESCE(GROUP_CONCAT(DISTINCT dt.name), '') AS tags
                    FROM dishes d
                    LEFT JOIN dish_tag_map dtm ON d.id = dtm.dish_id
                    LEFT JOIN dish_tags dt ON dtm.tag_id = dt.id
                    WHERE d.is_available IS NULL OR d.is_available = 1
                    GROUP BY d.id
                    ORDER BY d.id
                """
            else:
                query = """
                    SELECT d.id, d.name, d.description, '' AS tags
                    FROM dishes d
                    WHERE d.is_available IS NULL OR d.is_available = 1
                    ORDER BY d.id
                """
            result = conn.execute(text(query))
            return [dict(row._mapping) for row in result]

    @staticmethod
    def _table_exists(conn, table_name: str) -> bool:
        try:
            inspector = db.engine
            from sqlalchemy import inspect
            inspector_obj = inspect(inspector)
            return table_name in inspector_obj.get_table_names()
        except Exception:
            return False

    def _dish_to_text(self, dish: Dict) -> str:
        parts = [dish.get("name", "")]
        if dish.get("description"):
            parts.append(dish["description"])
        if dish.get("tags"):
            parts.append(f"Теги: {dish['tags']}")
        return " | ".join([p for p in parts if p])

    def _prepare_vectors(self, texts: List[str]) -> np.ndarray:
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype("float32")

    def rebuild(self) -> None:
        dishes = self._fetch_dishes_with_tags()
        if not dishes:
            with self.lock:
                self.index = faiss.IndexFlatIP(self.vector_size)
                self.metadata = []
                self._save_index()
            return
        texts = [self._dish_to_text(d) for d in dishes]
        vectors = self._prepare_vectors(texts)
        with self.lock:
            self.index = faiss.IndexFlatIP(self.vector_size)
            self.index.add(vectors)
            self.metadata = dishes
            self._save_index()

    async def rebuild_async(self) -> None:
        await asyncio.to_thread(self.rebuild)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict]:
        with self.lock:
            if self.index is None or self.index.ntotal == 0:
                return []
            top_k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(query_vector, top_k)
            results = []
            for score_list, idx_list in zip(distances, indices):
                for score, idx in zip(score_list, idx_list):
                    if idx == -1 or idx >= len(self.metadata):
                        continue
                    dish = self.metadata[idx]
                    results.append(
                        {
                            "id": dish["id"],
                            "name": dish["name"],
                            "description": dish.get("description"),
                            "tags": dish.get("tags", ""),
                            "score": float(score),
                        }
                    )
            return results

    def embed_tags(self, tags: List[str]) -> np.ndarray:
        text = ", ".join(tags)
        vector = self._prepare_vectors([text])
        return vector

    def format_context(self, dishes: List[Dict]) -> str:
        lines = []
        for dish in dishes:
            parts = [f"{dish['name']} (id={dish['id']})"]
            if dish.get("description"):
                parts.append(dish["description"])
            if dish.get("tags"):
                parts.append(f"Теги: {dish['tags']}")
            parts.append(f"score={dish['score']:.3f}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)


dish_vector_store = DishVectorStore()


async def periodic_embeddings_refresh(interval_seconds: int = 3600) -> None:
    while True:
        try:
            await dish_vector_store.rebuild_async()
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)
