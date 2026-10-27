# 知识库管理与可追溯 RAG 回复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 FastAPI 客服系统中建立文本知识条目、版本、发布状态和可追溯 RAG 回复闭环。

**Architecture:** 保持现有 `create_app(database_path=...)` 测试入口和统一响应格式。知识管理先落在现有数据库适配层中，向量检索通过独立接口隔离，发布时同步建立索引；客户消息路由改为先检索已发布知识，再将证据传给本地 LLM，最终保存证据快照。

**Tech Stack:** FastAPI, Pydantic v2, SQLite/MySQL adapter, pytest, httpx, Milvus adapter, local llama-server.

---

### Task 1: 知识条目与版本持久化

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_knowledge_flow.py`

- [x] **Step 1: Write failing API tests**

覆盖以下行为：

```python
def test_create_knowledge_starts_as_draft(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)
    result = client.post(
        "/api/v1/knowledge",
        json={"title": "订单物流服务规范", "category": "物流", "content": "物流状态会在承诺时效内更新。"},
    )
    assert result.status_code == 200
    assert result.json()["data"]["status"] == "DRAFT"
    assert result.json()["data"]["current_version"] == 1


def test_published_knowledge_cannot_be_edited_in_place(tmp_path):
    app = create_app(database_path=tmp_path / "support.db")
    client = TestClient(app)
    created = client.post(
        "/api/v1/knowledge",
        json={"title": "订单物流服务规范", "category": "物流", "content": "物流状态会在承诺时效内更新。"},
    ).json()["data"]
    published = client.post(
        f"/api/v1/knowledge/{created['knowledge_id']}/publish",
        json={"version": 1},
    )
    assert published.status_code == 200
    update = client.post(
        f"/api/v1/knowledge/{created['knowledge_id']}/versions",
        json={"content": "新的物流处理规则。", "source_note": "客服运营部"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["version"] == 2
    assert update.json()["data"]["status"] == "DRAFT"
```

- [x] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python3 -m pytest -q backend/tests/test_knowledge_flow.py
```

Expected: 404 responses because knowledge routes do not exist.

- [x] **Step 3: Add schema and request models**

在 `SCHEMA` 中增加 `knowledge_items` 和 `knowledge_versions` 表；新增 `KnowledgeInput`、`KnowledgeVersionInput`、`KnowledgePublishInput`，并将创建、版本、发布状态限制在文档方案规定的枚举值内。

- [x] **Step 4: Implement CRUD and publish routes**

实现：

```text
POST /api/v1/knowledge
GET  /api/v1/knowledge
GET  /api/v1/knowledge/{knowledge_id}
POST /api/v1/knowledge/{knowledge_id}/versions
POST /api/v1/knowledge/{knowledge_id}/publish
POST /api/v1/knowledge/{knowledge_id}/archive
```

创建知识时同时创建版本 1 草稿；发布时只切换数据库状态并写入审计事件，向量索引由 Task 3 接入。

- [x] **Step 5: Run focused and existing backend tests**

Run:

```bash
python3 -m pytest -q backend/tests/test_knowledge_flow.py backend/tests/test_support_flow.py
```

Expected: all tests pass.

### Task 2: 向量存储和 embedding 边界

**Files:**
- Modify: `backend/app/vector_store.py`
- Create: `backend/app/embeddings.py`
- Create: `backend/tests/test_embeddings.py`
- Modify: `backend/tests/test_vector_store.py`

- [x] **Step 1: Test deterministic local embedding and published-document filtering**
- [x] **Step 2: Verify the new tests fail because the interfaces do not exist**
- [x] **Step 3: Add `EmbeddingProvider` and deterministic development implementation**
- [x] **Step 4: Add `KnowledgeVectorStore.index_version`, `search`, and `delete_version`**
- [x] **Step 5: Keep Milvus SDK access inside the adapter and add an in-memory test implementation**
- [x] **Step 6: Run all backend tests**

### Task 3: 发布索引和 RAG 路由

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_knowledge_flow.py`
- Create: `backend/tests/test_rag_flow.py`

- [ ] **Step 1: Add failing tests for publish indexing and evidence-bearing replies**
- [ ] **Step 2: Verify failures**
- [ ] **Step 3: Inject vector store and embedding provider into `create_app`**
- [ ] **Step 4: Index only the published version and roll back publication when indexing fails**
- [ ] **Step 5: Replace hardcoded FAQ context with search results**
- [ ] **Step 6: Return `evidence`, `confidence`, and `handoff_required`**
- [ ] **Step 7: Add low-confidence refusal and `low_confidence` human transfer**
- [ ] **Step 8: Run the complete backend suite**

### Task 4: Evidence persistence and audit queries

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_rag_flow.py`

- [ ] **Step 1: Add failing tests for `message_evidence` snapshots and audit retrieval**
- [ ] **Step 2: Verify failures**
- [ ] **Step 3: Add the evidence table and save immutable evidence snapshots**
- [ ] **Step 4: Add `GET /api/v1/knowledge/{id}/evidence`**
- [ ] **Step 5: Add audit events for create, publish, archive, and citation**
- [ ] **Step 6: Run backend tests and `git diff --check`**

### Task 5: Knowledge management and evidence UI

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/styles.css`
- Create: `frontend/src/knowledge.test.tsx`

- [ ] **Step 1: Add failing component/API tests for list, publish, archive, and evidence rendering**
- [ ] **Step 2: Verify failures**
- [ ] **Step 3: Add typed knowledge API functions**
- [ ] **Step 4: Add a working knowledge view and navigation state**
- [ ] **Step 5: Render real evidence on robot messages and explicit handoff state on refusal**
- [ ] **Step 6: Run frontend tests and production build**

### Task 6: End-to-end verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-10-27-knowledge-rag-design.md`
- Create: `backend/tests/test_knowledge_rag_integration.py`

- [ ] **Step 1: Add the complete create → publish → ask → cite integration test**
- [ ] **Step 2: Run backend and frontend verification commands**
- [ ] **Step 3: Document local embedding configuration, Milvus readiness, and safe refusal behavior**
- [ ] **Step 4: Confirm no credentials or generated database/volume files are tracked**
