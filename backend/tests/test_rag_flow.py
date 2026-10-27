import sqlite3

from fastapi.testclient import TestClient

from app.embeddings import DeterministicEmbeddingProvider
from app.main import create_app
from app.vector_store import InMemoryKnowledgeStore


class FixedEmbeddingProvider:
    dimension = 2

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]


class RecordingLlamaClient:
    def __init__(self):
        self.context = None

    def answer(self, question: str, context: str) -> str:
        self.context = context
        return "根据已发布物流规范，物流状态会在承诺时效内更新。"


def test_publishing_knowledge_indexes_its_content(tmp_path):
    vector_store = InMemoryKnowledgeStore()
    embedding_provider = DeterministicEmbeddingProvider(dimension=8)
    app = create_app(
        database_path=tmp_path / "support.db",
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    client = TestClient(app)

    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
        },
    ).json()["data"]

    response = client.post(
        f"/api/v1/knowledge/{created['knowledge_id']}/publish",
        json={"version": 1},
    )

    assert response.status_code == 200
    matches = vector_store.search(
        embedding_provider.embed("订单物流服务规范\n物流状态会在承诺时效内更新。"),
    )
    assert matches[0]["knowledge_id"] == created["knowledge_id"]
    assert matches[0]["version"] == 1


def test_publish_keeps_draft_when_vector_indexing_fails(tmp_path):
    class FailingStore(InMemoryKnowledgeStore):
        def index_version(self, *args, **kwargs):
            raise RuntimeError("vector store offline")

    app = create_app(
        database_path=tmp_path / "support.db",
        vector_store=FailingStore(),
        embedding_provider=DeterministicEmbeddingProvider(dimension=8),
    )
    client = TestClient(app, raise_server_exceptions=False)

    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
        },
    ).json()["data"]

    response = client.post(
        f"/api/v1/knowledge/{created['knowledge_id']}/publish",
        json={"version": 1},
    )

    assert response.status_code == 503
    detail = client.get(f"/api/v1/knowledge/{created['knowledge_id']}").json()["data"]
    assert detail["status"] == "DRAFT"
    assert detail["versions"][0]["status"] == "DRAFT"


def test_publishing_new_version_replaces_previous_vector(tmp_path):
    vector_store = InMemoryKnowledgeStore()
    embedding_provider = DeterministicEmbeddingProvider(dimension=8)
    app = create_app(
        database_path=tmp_path / "support.db",
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    client = TestClient(app)

    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "旧版物流规则。",
        },
    ).json()["data"]
    knowledge_id = created["knowledge_id"]
    client.post(f"/api/v1/knowledge/{knowledge_id}/publish", json={"version": 1})
    client.post(
        f"/api/v1/knowledge/{knowledge_id}/versions",
        json={"content": "新版物流规则。"},
    )

    response = client.post(f"/api/v1/knowledge/{knowledge_id}/publish", json={"version": 2})

    assert response.status_code == 200
    old_matches = vector_store.search(embedding_provider.embed("订单物流服务规范\n旧版物流规则。"))
    new_matches = vector_store.search(embedding_provider.embed("订单物流服务规范\n新版物流规则。"))
    assert all(match["version"] != 1 for match in old_matches)
    assert new_matches[0]["version"] == 2


def test_customer_faq_reply_uses_retrieved_evidence(tmp_path):
    vector_store = InMemoryKnowledgeStore()
    embedding_provider = FixedEmbeddingProvider()
    llama_client = RecordingLlamaClient()
    app = create_app(
        database_path=tmp_path / "support.db",
        llm_client=llama_client,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    client = TestClient(app)

    knowledge = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
        },
    ).json()["data"]
    client.post(
        f"/api/v1/knowledge/{knowledge['knowledge_id']}/publish",
        json={"version": 1},
    )
    session = client.post(
        "/api/v1/sessions",
        json={"customer_name": "林晓", "channel": "web"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={
            "client_msg_id": "faq-001",
            "sender_type": "customer",
            "content": "物流多久更新？",
            "msg_type": "text",
        },
    )

    data = response.json()["data"]
    assert data["handler"] == "robot"
    assert data["handoff_required"] is False
    assert data["reply_message_id"]
    assert data["evidence"][0]["knowledge_id"] == knowledge["knowledge_id"]
    assert data["evidence"][0]["version"] == 1
    assert "订单物流服务规范 v1" in llama_client.context

    evidence_response = client.get(
        f"/api/v1/knowledge/{knowledge['knowledge_id']}/evidence",
    )

    assert evidence_response.status_code == 200
    snapshots = evidence_response.json()["data"]
    assert len(snapshots) == 1
    assert snapshots[0]["message_id"] == data["reply_message_id"]
    assert snapshots[0]["knowledge_id"] == knowledge["knowledge_id"]
    assert snapshots[0]["version"] == 1
    assert snapshots[0]["chunk_text"] == "物流状态会在承诺时效内更新。"
    assert snapshots[0]["title"] == "订单物流服务规范"

    with sqlite3.connect(tmp_path / "support.db") as database:
        audit_types = database.execute(
            "SELECT event_type FROM audit_events WHERE session_id = ?",
            (session["session_id"],),
        ).fetchall()
    assert ("KNOWLEDGE_CITED",) in audit_types


def test_customer_question_without_evidence_is_transferred_to_human(tmp_path):
    app = create_app(
        database_path=tmp_path / "support.db",
        llm_client=RecordingLlamaClient(),
        vector_store=InMemoryKnowledgeStore(),
        embedding_provider=FixedEmbeddingProvider(),
    )
    client = TestClient(app)
    session = client.post(
        "/api/v1/sessions",
        json={"customer_name": "林晓", "channel": "web"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={
            "client_msg_id": "faq-no-match-001",
            "sender_type": "customer",
            "content": "请解释一个没有知识来源的问题。",
            "msg_type": "text",
        },
    )

    data = response.json()["data"]
    assert data["handler"] == "human"
    assert data["handoff_required"] is True
    assert data["reply"] == "暂未找到可以确认该问题的已发布知识。我可以为您转接人工客服继续处理。"
    assert data["evidence"] == []
    assert data["session"]["status"] == "HUMAN_HANDLING"
    assert data["session"]["transfer_reason"] == "low_confidence"
