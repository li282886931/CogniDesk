from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Protocol


def knowledge_collection_name(_: str = "") -> str:
    return os.getenv("MILVUS_COLLECTION", "customer_support_knowledge")


@dataclass(frozen=True)
class MilvusConfig:
    host: str = os.getenv("MILVUS_HOST", "127.0.0.1")
    port: int = int(os.getenv("MILVUS_PORT", "19530"))
    collection: str = knowledge_collection_name()
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "32"))


class KnowledgeVectorStore(Protocol):
    def index_version(
        self,
        knowledge_id: str,
        version: int,
        title: str,
        content: str,
        source: str,
        vector: Iterable[float],
    ) -> None:
        ...

    def search(self, vector: Iterable[float], limit: int = 5) -> list[dict[str, Any]]:
        ...

    def delete_version(self, knowledge_id: str, version: int) -> None:
        ...


def _cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values):
        raise ValueError("vectors must have the same dimension")
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left_values, right_values)) / (left_norm * right_norm)


class InMemoryKnowledgeStore:
    def __init__(self):
        self._records: dict[tuple[str, int], dict[str, Any]] = {}

    def index_version(
        self,
        knowledge_id: str,
        version: int,
        title: str,
        content: str,
        source: str,
        vector: Iterable[float],
    ) -> None:
        self._records[(knowledge_id, version)] = {
            "knowledge_id": knowledge_id,
            "version": version,
            "title": title,
            "content": content,
            "source": source,
            "vector": list(vector),
        }

    def search(self, vector: Iterable[float], limit: int = 5) -> list[dict[str, Any]]:
        query = list(vector)
        ranked = []
        for record in self._records.values():
            result = {key: value for key, value in record.items() if key != "vector"}
            result["score"] = _cosine_similarity(query, record["vector"])
            ranked.append(result)
        ranked.sort(key=lambda item: (-item["score"], item["knowledge_id"], item["version"]))
        return ranked[:limit]

    def delete_version(self, knowledge_id: str, version: int) -> None:
        self._records.pop((knowledge_id, version), None)


class MilvusKnowledgeStore:
    def __init__(self, config: Optional[MilvusConfig] = None):
        self.config = config or MilvusConfig()
        self._connected = False

    def connect(self) -> Any:
        from pymilvus import connections

        if not self._connected:
            connections.connect(
                alias="default",
                host=self.config.host,
                port=self.config.port,
            )
            self._connected = True
        return connections

    def _collection(self) -> Any:
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

        self.connect()
        if not utility.has_collection(self.config.collection):
            fields = [
                FieldSchema(name="item_id", dtype=DataType.VARCHAR, is_primary=True, max_length=160),
                FieldSchema(name="knowledge_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="version", dtype=DataType.INT64),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=160),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.config.dimension),
            ]
            collection = Collection(
                name=self.config.collection,
                schema=CollectionSchema(fields=fields, description="Published customer support knowledge"),
            )
            collection.create_index(
                field_name="embedding",
                index_params={"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}},
            )
            return collection
        return Collection(self.config.collection)

    def index_version(
        self,
        knowledge_id: str,
        version: int,
        title: str,
        content: str,
        source: str,
        vector: Iterable[float],
    ) -> None:
        vector_values = list(vector)
        if len(vector_values) != self.config.dimension:
            raise ValueError("vector dimension does not match Milvus configuration")
        collection = self._collection()
        self.delete_version(knowledge_id, version)
        collection.insert(
            [[f"{knowledge_id}:v{version}"], [knowledge_id], [version], [title], [content], [source], [vector_values]]
        )
        collection.flush()

    def search(self, vector: Iterable[float], limit: int = 5) -> list[dict[str, Any]]:
        vector_values = list(vector)
        if len(vector_values) != self.config.dimension:
            raise ValueError("vector dimension does not match Milvus configuration")
        collection = self._collection()
        collection.load()
        results = collection.search(
            data=[vector_values],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=limit,
            output_fields=["knowledge_id", "version", "title", "content", "source"],
        )
        matches = []
        for hit in results[0]:
            entity = hit.entity
            matches.append(
                {
                    "knowledge_id": entity.get("knowledge_id"),
                    "version": entity.get("version"),
                    "title": entity.get("title"),
                    "content": entity.get("content"),
                    "source": entity.get("source"),
                    "score": float(hit.distance),
                }
            )
        return matches

    def delete_version(self, knowledge_id: str, version: int) -> None:
        collection = self._collection()
        collection.delete(f'knowledge_id == "{knowledge_id}" and version == {version}')
