from app.vector_store import MilvusConfig, knowledge_collection_name


def test_milvus_config_uses_local_defaults():
    config = MilvusConfig()

    assert config.host == "127.0.0.1"
    assert config.port == 19530
    assert knowledge_collection_name("Customer FAQ") == "customer_support_knowledge"
