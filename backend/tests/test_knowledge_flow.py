from fastapi.testclient import TestClient

from app.main import create_app


def test_create_knowledge_starts_as_draft(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)

    result = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
        },
    )

    assert result.status_code == 200
    data = result.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["current_version"] == 1
    assert data["versions"][0]["version"] == 1
    assert data["versions"][0]["status"] == "DRAFT"


def test_published_knowledge_creates_a_new_draft_version(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)

    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "订单物流服务规范",
            "category": "物流",
            "content": "物流状态会在承诺时效内更新。",
        },
    ).json()["data"]
    knowledge_id = created["knowledge_id"]

    published = client.post(
        f"/api/v1/knowledge/{knowledge_id}/publish",
        json={"version": 1},
    )

    assert published.status_code == 200
    assert published.json()["data"]["status"] == "PUBLISHED"

    update = client.post(
        f"/api/v1/knowledge/{knowledge_id}/versions",
        json={"content": "新的物流处理规则。", "source_note": "客服运营部"},
    )

    assert update.status_code == 200
    version = update.json()["data"]
    assert version["version"] == 2
    assert version["status"] == "DRAFT"
