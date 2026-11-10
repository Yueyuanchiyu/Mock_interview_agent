# 架构说明

## 设计原则

1. 业务数据库是面试事实源，Agent Checkpoint 不是业务数据库的替代品。
2. LLM 输出使用 Pydantic 结构化模型，失败时才进入确定性降级。
3. Agent 状态、业务服务、持久化和基础设施相互分层。
4. RAG 只保留一套主实现：Chroma 向量召回 + MySQL 关键词召回。
5. 所有外部能力通过 Service 或 Tool 暴露，方便继续接入 MCP。
6. 不把验证码、邮件、数据库写入等敏感副作用交给模型自由决定。

## 请求链路

```text
POST /interview/answer
  -> 解析并校验 JWT
  -> AgentWorkflow.answer
  -> LangGraph route=answer
  -> load_round
  -> retrieve_context
  -> evaluate_answer
  -> persist_answer
  -> generate_followup?
  -> update_checkpoint
  -> response
```

## 状态、上下文和 Store

- Context：当前题目、RAG 证据、回答和历史追问，经 `ContextBudget` 按 Token 预算装配。
- State：LangGraph `InterviewState`，按 `session_id` 隔离，可被 Checkpointer 持久化。
- Store：Redis 保存跨会话用户薄弱点和偏好，`AgentMemoryStore` 提供稳定接口。

## 工具与 Middleware

`agent/tools.py` 使用 LangChain `StructuredTool` 定义只读工具。资源顾问通过 `create_agent` 实际进行工具调用。

未来 Middleware 应集中处理：

- Prompt 注入和 PII 脱敏
- 模型路由、超时、回退
- 工具白名单、调用次数和循环上限
- 上下文压缩与 Token 预算
- Trace、Token、成本和节点耗时

## 选择与舍弃

保留：

- 原项目登录、抽题、评分、追问、报告、历史和成长功能
- LangGraph、Checkpointer、Redis、工具定义和 Chroma RAG
- 当前 Vue 3 工作台

舍弃：

- 让模型自由生成 SQL 的 MySQL Tool
- 两套 Agent 入口和旧 `chat` SSE 实验路由
- 两套 RAG（Chroma 与 FAISS）
- 硬编码数据库连接、邮箱和密钥
- 重复的旧目录及编译产物

