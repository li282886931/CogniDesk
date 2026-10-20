from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional


def knowledge_collection_name(_: str = "") -> str:
    return os.getenv("MILVUS_COLLECTION", "customer_support_knowledge")


@dataclass(frozen=True)
class MilvusConfig:
    host: str = os.getenv("MILVUS_HOST", "127.0.0.1")
    port: int = int(os.getenv("MILVUS_PORT", "19530"))
    collection: str = knowledge_collection_name()


class MilvusKnowledgeStore:
    def __init__(self, config: Optional[MilvusConfig] = None):
        self.config = config or MilvusConfig()

    def connect(self) -> Any:
        from pymilvus import connections

        connections.connect(
            alias="default",
            host=self.config.host,
            port=self.config.port,
        )
        return connections

    def search(self, vector: Iterable[float], limit: int = 5) -> list[dict[str, Any]]:
        from pymilvus import Collection

        collection = Collection(self.config.collection)
        collection.load()
        results = collection.search(
            data=[list(vector)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=limit,
            output_fields=["item_id", "content", "source"],
        )
        return [dict(hit.entity) for hit in results[0]]
