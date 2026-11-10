# 源文件筛选记录

## 从 `A05-AI_mock_interciew_software` 保留的设计

| 源能力 | 处理 |
|---|---|
| LangGraph StateGraph、InterviewState | 保留，按 Start/Answer/Followup/Next/Finish 拆为独立节点 |
| AsyncPostgresSaver、thread_id | 保留，改为可选 Checkpointer |
| MySQL / Redis / Email / Word 工具思路 | 保留，移除模型自由生成 SQL |
| Tool Calling Agent | 保留，重做为只读资源顾问 |
| FAISS RAG | 舍弃，统一到成熟度更高的 Chroma 实现 |
| 旧 `/chat` SSE Agent 路由 | 舍弃，业务接口统一到 `/interview/*` |
| 硬编码数据库名和连接 | 舍弃，全部进入 Settings |
| 空 FAISS 文件和生成物料 | 不迁移 |
| Vosk 服务端录音 | 暂不迁移；当前前端保留 Web Speech API |

## 从 `A05-AI_mock_interciew_software1` 保留的设计

| 模块 | 处理 |
|---|---|
| FastAPI 模块化结构 | 保留并进一步按 api/agent/services/repositories 分层 |
| 登录、验证码、面试、追问、报告 | 保留业务行为 |
| Chroma + BGE RAG | 保留并统一为唯一 RAG 实现 |
| 评分、资源推荐、成长统计 | 保留并增加结构化输出与降级 |
| Vue 3 界面 | 保留，增加 JWT 与路由守卫 |
| 旧 `core/infrastructure/modules` 层级 | 调整为更适合 Agent 项目的职责边界 |

## 新项目新增

- JWT 会话认证和会话归属校验
- LangGraph 主业务工作流
- Redis 长期记忆 Store
- 上下文 Token 预算
- LangChain StructuredTool 与工具型资源顾问
- Pydantic LLM 结构化输出
- 报告幂等写入与数据库唯一约束
- 测试、Nginx 示例和环境模板

## 明确不迁移

- 虚拟环境和 `node_modules`
- 真实 `.env`、密钥、邮箱授权码
- `__pycache__`、日志和旧报告
- 重复前端和旧 webpack 构建目录
- 模型可任意执行 SQL 的 MySQL Tool

