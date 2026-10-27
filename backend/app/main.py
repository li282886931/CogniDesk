from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .database import Connection, connect
from .llm import LocalLlamaClient

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def response(data: Any, message: str = "ok") -> Dict[str, Any]:
    return {"code": 0, "message": message, "data": data, "request_id": f"req_{uuid.uuid4().hex[:12]}"}


class SessionInput(BaseModel):
    customer_name: str = Field(min_length=1, max_length=80)
    channel: str = Field(default="web", pattern="^(web|app|miniapp|wechatwork)$")


class MessageInput(BaseModel):
    client_msg_id: str = Field(min_length=1, max_length=128)
    sender_type: str = Field(pattern="^(customer|robot|agent|system)$")
    content: str = Field(min_length=1, max_length=4000)
    msg_type: str = Field(default="text", pattern="^(text|image|file)$")


class TransferInput(BaseModel):
    reason: str = Field(default="user_request", pattern="^(user_request|low_confidence|negative_sentiment|sensitive_intent|unresolved)$")
    expect_skill: Optional[str] = Field(default=None, max_length=80)


class TicketInput(BaseModel):
    session_id: str
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    priority: str = Field(default="P2", pattern="^(P1|P2|P3)$")
    summary: str = Field(min_length=1, max_length=2000)


class KnowledgeInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=20000)
    source_note: Optional[str] = Field(default=None, max_length=255)


class KnowledgeVersionInput(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    source_note: Optional[str] = Field(default=None, max_length=255)


class KnowledgePublishInput(BaseModel):
    version: int = Field(ge=1)


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    created_at VARCHAR(40) NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    assignee_name VARCHAR(80),
    transfer_reason VARCHAR(64),
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    client_msg_id VARCHAR(128) NOT NULL,
    sender_type VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    msg_type VARCHAR(16) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    UNIQUE(session_id, client_msg_id),
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    title VARCHAR(160) NOT NULL,
    category VARCHAR(80) NOT NULL,
    priority VARCHAR(8) NOT NULL,
    status VARCHAR(32) NOT NULL,
    summary TEXT NOT NULL,
    sla_due_at VARCHAR(40) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    detail VARCHAR(255) NOT NULL,
    created_at VARCHAR(40) NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_items (
    knowledge_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(160) NOT NULL,
    category VARCHAR(80) NOT NULL,
    status VARCHAR(24) NOT NULL,
    current_version INTEGER NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    updated_by VARCHAR(64) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_versions (
    version_id VARCHAR(64) PRIMARY KEY,
    knowledge_id VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(24) NOT NULL,
    source_note VARCHAR(255),
    effective_from VARCHAR(40),
    effective_until VARCHAR(40),
    created_by VARCHAR(64) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    UNIQUE(knowledge_id, version),
    FOREIGN KEY(knowledge_id) REFERENCES knowledge_items(knowledge_id)
);
"""


def create_app(database_path: Optional[Path] = None, llm_client: Optional[LocalLlamaClient] = None) -> FastAPI:
    app = FastAPI(title="Support Console API", version="0.1.0")
    model_client = llm_client or LocalLlamaClient()

    @contextmanager
    def db() -> Generator[Connection, None, None]:
        connection = connect(database_path)
        connection.executescript(SCHEMA)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def session_payload(row: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(row)
        payload["customer_name"] = payload.pop("name")
        return payload

    def get_session(connection: Connection, session_id: str) -> Dict[str, Any]:
        row = connection.execute(
            """
            SELECT s.*, c.name
            FROM sessions s JOIN customers c ON c.customer_id = s.customer_id
            WHERE s.session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="session not found")
        return row

    def add_audit(connection: Connection, session_id: Optional[str], event_type: str, detail: str) -> None:
        connection.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?)",
            (f"evt_{uuid.uuid4().hex[:12]}", session_id, event_type, detail, now()),
        )

    def transfer(connection: Connection, session_id: str, reason: str) -> Dict[str, Any]:
        current = get_session(connection, session_id)
        if current["status"] != "HUMAN_HANDLING":
            timestamp = now()
            connection.execute(
                "UPDATE sessions SET status = ?, transfer_reason = ?, updated_at = ? WHERE session_id = ?",
                ("HUMAN_HANDLING", reason, timestamp, session_id),
            )
            add_audit(connection, session_id, "TRANSFER_TO_HUMAN", reason)
        return get_session(connection, session_id)

    def get_knowledge(connection: Connection, knowledge_id: str) -> Dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM knowledge_items WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="knowledge not found")
        versions = connection.execute(
            "SELECT * FROM knowledge_versions WHERE knowledge_id = ? ORDER BY version DESC",
            (knowledge_id,),
        ).fetchall()
        payload = dict(row)
        payload["versions"] = [dict(version) for version in versions]
        return payload

    def route_customer_message(content: str) -> Dict[str, Any]:
        normalized = content.lower()
        if any(keyword in normalized for keyword in ("退款", "改密", "身份证", "人工", "投诉")):
            return {"handler": "human", "reason": "sensitive_intent"}
        if any(keyword in normalized for keyword in ("生气", "愤怒", "差评")):
            return {"handler": "human", "reason": "negative_sentiment"}
        if any(keyword in normalized for keyword in ("发货", "物流", "订单")):
            source = "订单物流服务规范 v1.0"
            generated = model_client.answer(
                question=content,
                context="已发布知识：订单物流服务规范 v1.0。物流超过承诺时效时，可协助客户转人工核查。",
            )
            return {
                "handler": "robot",
                "reply": generated or "已根据订单物流知识为您检索。若超过承诺时效未更新，我会立即为您转人工处理。",
                "source": source,
            }
        return {"handler": "robot", "reply": "暂未找到可引用的已发布知识。我可以现在为您转接人工客服继续处理。"}

    @app.get("/api/v1/health")
    def health() -> Dict[str, Any]:
        return response({"status": "healthy"})

    @app.post("/api/v1/knowledge")
    def create_knowledge(payload: KnowledgeInput) -> Dict[str, Any]:
        knowledge_id = f"kn_{uuid.uuid4().hex[:12]}"
        version_id = f"knv_{uuid.uuid4().hex[:12]}"
        timestamp = now()
        with db() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_items
                (knowledge_id, title, category, status, current_version, created_by, updated_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (knowledge_id, payload.title, payload.category, "DRAFT", 1, "local-admin", "local-admin", timestamp, timestamp),
            )
            connection.execute(
                """
                INSERT INTO knowledge_versions
                (version_id, knowledge_id, version, content, status, source_note, effective_from, effective_until, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, knowledge_id, 1, payload.content, "DRAFT", payload.source_note, None, None, "local-admin", timestamp),
            )
            add_audit(connection, "system", "KNOWLEDGE_CREATED", knowledge_id)
            knowledge = get_knowledge(connection, knowledge_id)
        return response(knowledge)

    @app.get("/api/v1/knowledge")
    def list_knowledge(status: Optional[str] = Query(default=None), category: Optional[str] = Query(default=None)) -> Dict[str, Any]:
        with db() as connection:
            query = "SELECT * FROM knowledge_items"
            conditions = []
            args = []
            if status:
                conditions.append("status = ?")
                args.append(status)
            if category:
                conditions.append("category = ?")
                args.append(category)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY updated_at DESC"
            rows = connection.execute(query, args).fetchall()
        return response([dict(row) for row in rows])

    @app.get("/api/v1/knowledge/{knowledge_id}")
    def read_knowledge(knowledge_id: str) -> Dict[str, Any]:
        with db() as connection:
            knowledge = get_knowledge(connection, knowledge_id)
        return response(knowledge)

    @app.post("/api/v1/knowledge/{knowledge_id}/versions")
    def create_knowledge_version(knowledge_id: str, payload: KnowledgeVersionInput) -> Dict[str, Any]:
        version_id = f"knv_{uuid.uuid4().hex[:12]}"
        timestamp = now()
        with db() as connection:
            knowledge = get_knowledge(connection, knowledge_id)
            latest_version = max((version["version"] for version in knowledge["versions"]), default=0)
            version = latest_version + 1
            connection.execute(
                """
                INSERT INTO knowledge_versions
                (version_id, knowledge_id, version, content, status, source_note, effective_from, effective_until, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, knowledge_id, version, payload.content, "DRAFT", payload.source_note, None, None, "local-admin", timestamp),
            )
            connection.execute(
                "UPDATE knowledge_items SET updated_by = ?, updated_at = ? WHERE knowledge_id = ?",
                ("local-admin", timestamp, knowledge_id),
            )
            add_audit(connection, "system", "KNOWLEDGE_VERSION_CREATED", f"{knowledge_id}:v{version}")
            created = connection.execute(
                "SELECT * FROM knowledge_versions WHERE version_id = ?",
                (version_id,),
            ).fetchone()
        return response(dict(created))

    @app.post("/api/v1/knowledge/{knowledge_id}/publish")
    def publish_knowledge(knowledge_id: str, payload: KnowledgePublishInput) -> Dict[str, Any]:
        timestamp = now()
        with db() as connection:
            knowledge = get_knowledge(connection, knowledge_id)
            selected = next((version for version in knowledge["versions"] if version["version"] == payload.version), None)
            if not selected:
                raise HTTPException(status_code=404, detail="knowledge version not found")
            if selected["status"] == "PUBLISHED":
                return response(knowledge)
            if selected["status"] != "DRAFT":
                raise HTTPException(status_code=409, detail="knowledge version cannot be published")
            connection.execute(
                "UPDATE knowledge_versions SET status = ?, effective_from = ? WHERE knowledge_id = ? AND status = ?",
                ("ARCHIVED", timestamp, knowledge_id, "PUBLISHED"),
            )
            connection.execute(
                "UPDATE knowledge_versions SET status = ?, effective_from = ? WHERE knowledge_id = ? AND version = ?",
                ("PUBLISHED", timestamp, knowledge_id, payload.version),
            )
            connection.execute(
                """
                UPDATE knowledge_items
                SET status = ?, current_version = ?, updated_by = ?, updated_at = ?
                WHERE knowledge_id = ?
                """,
                ("PUBLISHED", payload.version, "local-admin", timestamp, knowledge_id),
            )
            add_audit(connection, "system", "KNOWLEDGE_PUBLISHED", f"{knowledge_id}:v{payload.version}")
            published = get_knowledge(connection, knowledge_id)
        return response(published)

    @app.post("/api/v1/knowledge/{knowledge_id}/archive")
    def archive_knowledge(knowledge_id: str) -> Dict[str, Any]:
        timestamp = now()
        with db() as connection:
            get_knowledge(connection, knowledge_id)
            connection.execute(
                "UPDATE knowledge_items SET status = ?, updated_by = ?, updated_at = ? WHERE knowledge_id = ?",
                ("ARCHIVED", "local-admin", timestamp, knowledge_id),
            )
            connection.execute(
                "UPDATE knowledge_versions SET status = ? WHERE knowledge_id = ? AND status = ?",
                ("ARCHIVED", knowledge_id, "PUBLISHED"),
            )
            add_audit(connection, "system", "KNOWLEDGE_ARCHIVED", knowledge_id)
            archived = get_knowledge(connection, knowledge_id)
        return response(archived)

    @app.post("/api/v1/sessions")
    def create_session(payload: SessionInput) -> Dict[str, Any]:
        customer_id = f"cus_{uuid.uuid4().hex[:12]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        timestamp = now()
        with db() as connection:
            connection.execute("INSERT INTO customers VALUES (?, ?, ?, ?)", (customer_id, payload.customer_name, payload.channel, timestamp))
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, customer_id, payload.channel, "ROBOT_HANDLING", None, None, timestamp, timestamp),
            )
            add_audit(connection, session_id, "SESSION_CREATED", payload.channel)
            row = get_session(connection, session_id)
        return response(session_payload(row))

    @app.get("/api/v1/sessions")
    def list_sessions(status: Optional[str] = Query(default=None)) -> Dict[str, Any]:
        with db() as connection:
            query = "SELECT s.*, c.name FROM sessions s JOIN customers c ON c.customer_id = s.customer_id"
            args = []
            if status:
                query += " WHERE s.status = ?"
                args.append(status)
            query += " ORDER BY s.updated_at DESC"
            rows = connection.execute(query, args).fetchall()
        return response([session_payload(row) for row in rows])

    @app.get("/api/v1/sessions/{session_id}")
    def read_session(session_id: str) -> Dict[str, Any]:
        with db() as connection:
            row = get_session(connection, session_id)
            messages = connection.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
            tickets = connection.execute(
                "SELECT * FROM tickets WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        data = session_payload(row)
        data["messages"] = [dict(message) for message in messages]
        data["tickets"] = [dict(ticket) for ticket in tickets]
        return response(data)

    @app.post("/api/v1/sessions/{session_id}/messages")
    def send_message(session_id: str, payload: MessageInput) -> Dict[str, Any]:
        with db() as connection:
            session = get_session(connection, session_id)
            existing = connection.execute(
                "SELECT * FROM messages WHERE session_id = ? AND client_msg_id = ?",
                (session_id, payload.client_msg_id),
            ).fetchone()
            if existing:
                return response({"message_id": existing["message_id"], "session": session_payload(session), "handler": "idempotent"})
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, session_id, payload.client_msg_id, payload.sender_type, payload.content, payload.msg_type, now()),
            )
            handler = "agent"
            reply = None
            if payload.sender_type == "customer":
                route = route_customer_message(payload.content)
                handler = route["handler"]
                if handler == "human":
                    session = transfer(connection, session_id, route["reason"])
                else:
                    reply = route["reply"]
                    connection.execute(
                        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (f"msg_{uuid.uuid4().hex[:12]}", session_id, f"robot_{uuid.uuid4().hex[:12]}", "robot", reply, "text", now()),
                    )
                    connection.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now(), session_id))
            session = get_session(connection, session_id)
        return response({"message_id": message_id, "session_id": session_id, "handler": handler, "reply": reply, "session": session_payload(session)})

    @app.post("/api/v1/sessions/{session_id}/transfer")
    def transfer_to_human(session_id: str, payload: TransferInput) -> Dict[str, Any]:
        with db() as connection:
            session = transfer(connection, session_id, payload.reason)
        return response(session_payload(session))

    @app.post("/api/v1/tickets")
    def create_ticket(payload: TicketInput) -> Dict[str, Any]:
        ticket_id = f"tic_{uuid.uuid4().hex[:12]}"
        due_hours = {"P1": 4, "P2": 24, "P3": 72}[payload.priority]
        created_at = now()
        due_at = (datetime.now(timezone.utc) + timedelta(hours=due_hours)).isoformat()
        with db() as connection:
            get_session(connection, payload.session_id)
            connection.execute(
                "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ticket_id, payload.session_id, payload.title, payload.category, payload.priority, "OPEN", payload.summary, due_at, created_at),
            )
            connection.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                ("TICKET_CREATED", created_at, payload.session_id),
            )
            add_audit(connection, payload.session_id, "TICKET_CREATED", ticket_id)
            ticket = connection.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        return response(dict(ticket))

    @app.get("/api/v1/dashboard")
    def dashboard() -> Dict[str, Any]:
        with db() as connection:
            total = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            waiting = connection.execute("SELECT COUNT(*) FROM sessions WHERE status = 'HUMAN_HANDLING'").fetchone()[0]
            open_tickets = connection.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('OPEN', 'PROCESSING')").fetchone()[0]
        return response(
            {
                "active_sessions": total,
                "waiting_for_agent": waiting,
                "open_tickets": open_tickets,
                "ai_resolution_rate": 0.64,
                "csat": 0.88,
            }
        )

    return app


app = create_app()
