# MySQL Llama Milvus Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the support API to the existing Docker MySQL, connect FAQ replies to the local llama-server, and provide a persistent Docker Milvus standalone stack for future RAG indexing.

**Architecture:** Keep the existing FastAPI business routes and introduce a small database adapter that uses temporary SQLite in tests and MySQL in runtime. Add isolated local adapters for llama-server and Milvus, with all connection settings coming from environment variables. Compose runs Milvus with its own etcd and MinIO services so it does not conflict with the existing MinIO container.

**Tech Stack:** FastAPI, Python database adapter, MySQL 8, httpx, llama-server OpenAI-compatible API, Milvus standalone, etcd, MinIO, pytest.

---

### Task 1: Runtime configuration and database adapter

**Files:**
- Create: `backend/app/database.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml`
- Modify: `.gitignore`
- Create: `.env.example`

- [ ] Add `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, and `LLAMA_SERVER_URL` settings with MySQL as the production default.
- [ ] Keep `create_app(database_path=...)` on SQLite for isolated tests.
- [ ] Wrap connection creation, script execution, parameter translation, and row mapping behind one adapter.
- [ ] Run the existing tests before and after the change.

### Task 2: Local llama-server adapter

**Files:**
- Create: `backend/app/llm.py`
- Create: `backend/tests/test_llm.py`
- Modify: `backend/app/main.py`

- [ ] Test that an OpenAI-compatible completion is converted into a plain answer and that `<think>` blocks are removed.
- [ ] Test that timeout/unavailable model errors return a safe refusal result.
- [ ] Use the configured local model, disable thinking, enforce a short timeout, and never invent hard facts.
- [ ] Use the adapter only for knowledge-backed FAQ responses; sensitive intents continue to transfer to a human.

### Task 3: Milvus deployment and client boundary

**Files:**
- Create: `docker-compose.milvus.yml`
- Create: `backend/app/vector_store.py`
- Create: `backend/tests/test_vector_store.py`
- Modify: `.env.example`

- [ ] Define isolated `milvus`, `milvus-etcd`, and `milvus-minio` services with persistent volumes and host ports `19530`, `9091`, `9010`, and `9011`.
- [ ] Test collection naming and normalized vector-store configuration without requiring a live Milvus server.
- [ ] Keep the client optional so API tests do not require `pymilvus`; production setup documents installing it.
- [ ] Verify container health and Milvus HTTP readiness after startup.

### Task 4: MySQL initialization and verification

**Files:**
- Create: `backend/scripts/init_mysql.py`
- Create: `README.md`

- [ ] Create the `cognidesk` database and application tables using the supplied Docker credentials.
- [ ] Add a one-command local startup sequence for MySQL, Milvus, llama-server, backend, and frontend.
- [ ] Verify `/api/v1/health`, a MySQL-backed session creation, llama-server completion, and Milvus readiness.

### Task 5: Full regression and commit

**Files:**
- Modify: `backend/tests/test_support_flow.py`

- [ ] Run backend tests and frontend tests/build.
- [ ] Run `git diff --check` and confirm `.env` and database files are ignored.
- [ ] Commit the integration without credentials or generated runtime data.
