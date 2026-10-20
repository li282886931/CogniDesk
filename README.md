# CogniDesk

企业级在线客服与智能客服平台的一期可运行版本。系统提供客服坐席工作台、统一会话、机器人分流、转人工、工单、审计和运营指标，并预留 RAG 知识库能力。

## 功能范围

- 会话队列：查看待人工接入会话、客户画像和会话状态。
- 智能分流：退款、改密、投诉、人工请求等敏感意图自动转人工。
- 本地模型：调用本机 `llama-server` 生成 FAQ 回复；无可靠知识时拒识，不编造订单、日期、价格或技术参数。
- 工单处理：创建 P1/P2/P3 工单，自动计算 SLA 截止时间。
- 审计记录：会话创建、转人工和工单创建写入审计事件。
- 运营指标：进行中会话、待人工接入、待处理工单、AI 解决率和满意度。
- 基础向量层：通过 Docker Compose 部署 Milvus standalone，为知识库向量检索提供基础设施。

## 架构

```text
React + Vite 工作台 :5174
          │ /api 代理
FastAPI 业务服务 :8001
   ├── MySQL 8      业务数据、会话、消息、工单、审计
   ├── llama-server 本地大模型 :8080
   └── Milvus       向量检索 :19530 / HTTP :9091
                    ├── etcd
                    └── 专用 MinIO :9010 / Console :9011
```

后端运行时默认读取项目根目录 `.env`。`.env` 已被 Git 忽略，禁止提交真实密码。

## 环境要求

- macOS + Docker Desktop
- Python 3.11+
- Node.js 18+
- Docker 中运行的 MySQL 8，宿主机端口 `3306`
- 本地 llama-server，监听 `http://127.0.0.1:8080`

当前开发环境约定：

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 前端 | `http://127.0.0.1:5174` | Vite 开发服务器 |
| 后端 | `http://127.0.0.1:8001` | FastAPI |
| MySQL | `127.0.0.1:3306` | 数据库 `cognidesk` |
| llama-server | `127.0.0.1:8080` | OpenAI 兼容接口 |
| Milvus SDK | `127.0.0.1:19530` | 向量数据库 |
| Milvus HTTP | `http://127.0.0.1:9091` | 健康检查 |
| Milvus MinIO | `127.0.0.1:9010` | 对象存储 API |
| Milvus MinIO | `http://127.0.0.1:9011` | 控制台 |

## 配置

复制示例配置：

```bash
cp .env.example .env
```

按本机环境修改 `.env`：

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=<本机 MySQL 密码>
MYSQL_DATABASE=cognidesk

LLAMA_SERVER_URL=http://127.0.0.1:8080
LLAMA_MODEL=<llama-server 中实际加载的模型名>
LLAMA_TIMEOUT_SECONDS=30

MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=customer_support_knowledge

MINIO_ROOT_USER=root
MINIO_ROOT_PASSWORD=<Milvus 专用 MinIO 密码>
```

不要把密码写入 `README.md`、源代码、测试或提交记录。

## 启动步骤

### 1. 初始化 MySQL

项目会创建数据库 `cognidesk` 和一期业务表，不会删除已有数据库数据：

```bash
cd backend
python3 -m pip install -e '.[dev]'
python3 scripts/init_mysql.py
```

### 2. 启动 Milvus

Milvus 使用 standalone 模式，etcd、Milvus 和专用 MinIO 均由 Compose 管理，数据持久化在项目根目录 `volumes/`：

```bash
cd ..
docker compose -f docker-compose.milvus.yml up -d
docker compose -f docker-compose.milvus.yml ps
curl http://127.0.0.1:9091/healthz
```

停止但保留数据：

```bash
docker compose -f docker-compose.milvus.yml down
```

停止并删除 Milvus 数据：

```bash
docker compose -f docker-compose.milvus.yml down -v
rm -rf volumes/
```

### 3. 启动后端

```bash
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

健康检查：

```bash
curl http://127.0.0.1:8001/api/v1/health
```

### 4. 启动前端

新开终端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5174`。

## llama-server

后端调用 OpenAI 兼容接口：

```text
POST http://127.0.0.1:8080/v1/chat/completions
```

检查模型：

```bash
curl http://127.0.0.1:8080/v1/models
```

后端会：

- 使用 `.env` 中的 `LLAMA_MODEL`；
- 设置 `temperature=0`，降低随机编造；
- 限制生成长度；
- 移除 `<think>...</think>` 内容；
- 模型不可用或超时时回退到安全话术。

## API

统一响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_xxx"
}
```

一期接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/v1/health` | 服务健康检查 |
| POST | `/api/v1/sessions` | 创建会话 |
| GET | `/api/v1/sessions` | 查询会话队列，可按 `status` 筛选 |
| GET | `/api/v1/sessions/{id}` | 查询会话详情、消息和工单 |
| POST | `/api/v1/sessions/{id}/messages` | 发送消息，支持幂等键 `client_msg_id` |
| POST | `/api/v1/sessions/{id}/transfer` | 转人工 |
| POST | `/api/v1/tickets` | 创建工单并计算 SLA |
| GET | `/api/v1/dashboard` | 查询运营指标 |

创建会话示例：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"林晓","channel":"web"}'
```

## 测试与构建

后端测试：

```bash
python3 -m pytest -q backend/tests
```

前端测试和生产构建：

```bash
cd frontend
npm test
npm run build
```

数据库适配测试默认使用临时 SQLite，不依赖外部服务；运行应用时通过 `.env` 使用 MySQL。

## 常见问题

### MySQL 连接失败

确认容器和端口：

```bash
docker ps
nc -vz 127.0.0.1 3306
```

确认 `.env` 中的账号密码与当前 MySQL 容器实际配置一致，然后重新执行：

```bash
cd backend
python3 scripts/init_mysql.py
```

### Milvus 镜像拉取失败

先确认 Docker Desktop 正常运行并登录可用的镜像仓库：

```bash
docker login
docker compose -f docker-compose.milvus.yml pull
docker compose -f docker-compose.milvus.yml up -d
```

如果 macOS Docker Desktop 报 Keychain 错误，重启 Docker Desktop 后再执行；不要删除已有 MySQL、Redis 或 MinIO 容器。

### 前端端口冲突

前端固定使用 `5174`，后端固定使用 `8001`。如果仍冲突，修改 `frontend/vite.config.ts` 和后端启动命令，同时同步 README。

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── database.py       # SQLite 测试 / MySQL 运行时适配
│   │   ├── llm.py            # 本地 llama-server 适配器
│   │   ├── vector_store.py   # Milvus 客户端边界
│   │   └── main.py           # FastAPI 路由和业务状态机
│   ├── scripts/init_mysql.py # 建库和初始化表结构
│   └── tests/
├── frontend/src/             # React 工作台
├── docker-compose.milvus.yml # Milvus standalone 部署
├── .env.example              # 配置模板
└── PRODUCT.md                # 产品范围和长期约束
```

## 安全边界

- `.env`、数据库文件、构建产物和 Docker 数据卷不提交 Git。
- 生产环境应使用独立数据库用户，不应长期使用 root。
- 模型生成内容仅作为待核验证据，不能绕过人工审核直接执行敏感业务。
- Milvus、MinIO、MySQL 不应直接暴露到公网。
