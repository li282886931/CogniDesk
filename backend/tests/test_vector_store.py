from app.vector_store import InMemoryKnowledgeStore, MilvusConfig, knowledge_collection_name


def test_milvus_config_uses_local_defaults():
    config = MilvusConfig()

    assert config.host == "127.0.0.1"
    assert config.port == 19530
    assert config.dimension == 32
    assert knowledge_collection_name("Customer FAQ") == "customer_support_knowledge"


def test_in_memory_store_returns_only_indexed_published_versions():
    store = InMemoryKnowledgeStore()
    store.index_version(
        knowledge_id="kn_1",
        version=1,
        title="物流规范",
        content="物流状态会在承诺时效内更新。",
        source="物流规范 v1",
        vector=[1.0, 0.0],
    )
    store.index_version(
        knowledge_id="kn_2",
        version=1,
        title="退款规范",
        content="退款申请需要人工复核。",
        source="退款规范 v1",
        vector=[0.0, 1.0],
    )

    results = store.search([0.9, 0.1], limit=1)

    assert len(results) == 1
    assert results[0]["knowledge_id"] == "kn_1"
    assert results[0]["version"] == 1
    assert results[0]["source"] == "物流规范 v1"
    assert results[0]["score"] > 0.9


def test_in_memory_store_can_delete_a_published_version():
    store = InMemoryKnowledgeStore()
    store.index_version(
        knowledge_id="kn_1",
        version=1,
        title="物流规范",
        content="物流状态会在承诺时效内更新。",
        source="物流规范 v1",
        vector=[1.0, 0.0],
    )

    store.delete_version("kn_1", 1)

    assert store.search([1.0, 0.0]) == []
