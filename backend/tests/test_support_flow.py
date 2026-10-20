from fastapi.testclient import TestClient

from app.main import create_app


def test_customer_message_requests_human_and_creates_queue_item(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)

    session = client.post(
        "/api/v1/sessions",
        json={"customer_name": "林晓", "channel": "web"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/messages",
        json={
            "client_msg_id": "msg-human-001",
            "sender_type": "customer",
            "content": "我要人工客服处理退款问题",
            "msg_type": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handler"] == "human"
    assert data["session"]["status"] == "HUMAN_HANDLING"
    assert data["session"]["transfer_reason"] == "sensitive_intent"

    queue = client.get("/api/v1/sessions?status=HUMAN_HANDLING").json()["data"]
    assert [item["session_id"] for item in queue] == [session["session_id"]]


def test_agent_can_create_open_ticket_from_human_session(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)
    session = client.post(
        "/api/v1/sessions",
        json={"customer_name": "林晓", "channel": "web"},
    ).json()["data"]
    client.post(
        f"/api/v1/sessions/{session['session_id']}/transfer",
        json={"reason": "user_request"},
    )

    response = client.post(
        "/api/v1/tickets",
        json={
            "session_id": session["session_id"],
            "title": "退款人工复核",
            "category": "售后-退款",
            "priority": "P1",
            "summary": "客户明确要求人工处理退款。",
        },
    )

    assert response.status_code == 200
    ticket = response.json()["data"]
    assert ticket["status"] == "OPEN"
    assert ticket["session_id"] == session["session_id"]
