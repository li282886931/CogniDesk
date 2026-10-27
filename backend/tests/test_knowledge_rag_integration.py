from fastapi.testclient import TestClient

from app.main import create_app
from app.vector_store import InMemoryKnowledgeStore


class FixedEmbeddingProvider:
    dimension = 2

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]


class IntegrationLlamaClient:
    def answer(self, question: str, context: str) -> str:
        assert "订单物流服务规范 v1" in context
        return "物流状态会在承诺时效内更新。"


def test_create_publish_ask_and_reload_preserves_evidence(tmp_path):
    app = create_app(
        database_path=tmp_path / "support.db",
        llm_client=IntegrationLlamaClient(),
        vector_store=InMemoryKnowledgeStore(),
        embedding_provider=FixedEmbeddingProvider(),
    )
    client = TestClient(app)

    knowledge = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
            "source_note": "客服运营部",
        },
    ).json()["data"]
    published = client.post(
        f"/api/v1/knowledge/{knowledge['knowledge_id']}/publish",
        json={"version": 1},
    )
    assert published.status_code == 200

    session = client.post(
        "/api/v1/sessions",
        json={"customer_name": "林晓", "channel": "web"},
    ).json()["data"]
    reply = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={
            "client_msg_id": "integration-001",
            "sender_type": "customer",
            "content": "物流多久更新？",
            "msg_type": "text",
        },
    ).json()["data"]

    assert reply["handler"] == "robot"
    detail = client.get(f"/api/v1/sessions/{session['session_id']}").json()["data"]
    robot_messages = [message for message in detail["messages"] if message["sender_type"] == "robot"]

    assert robot_messages[-1]["evidence"][0]["knowledge_id"] == knowledge["knowledge_id"]
    assert robot_messages[-1]["evidence"][0]["source_note"] == "客服运营部"
