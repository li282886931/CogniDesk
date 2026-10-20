# CogniDesk

一期企业客服运营工作台，使用 FastAPI、React、MySQL、Milvus 和本地 llama-server。

## 本地启动

本机需要 Docker Desktop、Python 3.9+、Node.js，并确保已有：

- MySQL Docker 容器 `mysql8`，端口 `3306`
- llama-server，地址 `http://127.0.0.1:8080`

安装后端依赖并初始化数据库：

```bash
cd backend
python3 -m pip install -e '.[dev]'
python3 scripts/init_mysql.py
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

启动 Milvus：

```bash
docker compose -f docker-compose.milvus.yml up -d
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5174`。

Milvus 使用 standalone 模式，数据持久化在项目根目录的 `volumes/`，宿主机端口为 `19530`、`9091`；其专用 MinIO 使用 `9010`、`9011`，避免占用现有 MinIO 的 `9000`、`9001`。
