# Mock Interview Agent

面向技术岗位的 AI 模拟面试 Agent 应用。项目将现有面试产品能力整理为可运行主链路，并预留工具调用、LangGraph 状态、长短期记忆、上下文预算、Middleware 和 MCP 的扩展路径。

## 技术栈

- 后端：FastAPI、Pydantic、LangChain、LangGraph、MySQL、Redis
- RAG：ChromaDB、sentence-transformers、关键词召回
- 前端：Vue 3、Vite、Element Plus、ECharts、Web Speech API
- 报告：python-docx

## 目录

```text
Mock_interview_agent/
├─ backend/
│  ├─ app/
│  │  ├─ api/               # HTTP 接口和认证依赖
│  │  ├─ agent/             # LangGraph、状态、Prompt、Tool、记忆
│  │  ├─ services/          # 业务用例和 LLM 能力
│  │  ├─ repositories/      # MySQL 访问
│  │  ├─ infrastructure/    # LLM、数据库、Redis、邮件、RAG
│  │  ├─ schemas/           # API 与 LLM 输出模型
│  │  └─ core/              # 配置、日志、异常
│  ├─ scripts/              # 题库导入、向量索引构建
│  └─ tests/
├─ frontend/
├─ database/
├─ deploy/
└─ docs/
```

## 快速启动

### 1. 数据库

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p ai_mock_interview < database/seed.sql
```

如果已有原项目数据库，可直接复用原 `ai_mock_interview` 数据库。
演示种子中的 `demo@example.com` 不会实际收信，首次运行前请改成可登录邮箱。

### 2. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
# 填写 API Key、数据库密码、邮箱授权码和 JWT_SECRET
python -m app.main
```

接口文档：<http://127.0.0.1:8080/docs>

### 3. 构建 RAG 索引

```bash
cd backend
python -m scripts.build_vector_index
```

向量库不存在或构建失败时，面试流程会自动降级为 MySQL 关键词召回。

### 4. 前端

```bash
cd frontend
npm install
npm run dev
```

## Agent 运行模型

一次面试以 `session_id` 作为 LangGraph `thread_id`，状态中包含轮次、题目、上下文、评分、追问和长期记忆摘要。当前默认使用内存 Checkpointer，适合开发；生产可通过 `AGENT_CHECKPOINT_BACKEND=postgres` 切换 PostgreSQL。

核心分层：

```text
FastAPI Router
  -> AgentWorkflow
    -> LangGraph StateGraph
      -> Services
        -> Repositories / LLM / RAG
```

工具位于 `backend/app/agent/tools.py`，已经使用 LangChain `@tool`，并提供工具型资源顾问 Agent。后续可继续接入 MCP Adapter，而不改变面试主流程接口。

## 现有能力

- 邮箱验证码登录、JWT 认证
- 岗位抽题、历史题目过滤
- 文本和浏览器语音回答
- LLM 七维结构化评分、规则降级
- 动态追问、追问记录
- Chroma 向量检索、关键词召回、上下文预算
- 综合总结、学习资源推荐、Word 报告
- 历史记录、成长趋势
- LangGraph 状态和可选 Checkpointer
- Redis 长期记忆 Store 扩展点
- LangChain Tool Calling 工具型资源顾问
- Agent Checkpoint 状态查询接口

## 验证

```bash
cd backend
python -m compileall -q app scripts
pytest
```

详细设计与后续路线见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 和 [docs/ROADMAP.md](docs/ROADMAP.md)。

