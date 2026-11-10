# Agent 演进路线

## P0：主链路稳定

- 完成真实数据库和模型联调
- 为 LangGraph 节点加入执行轨迹与耗时记录
- 为面试提交增加幂等键
- 为报告和追问增加完整自动化测试
- 登录、会话归属和越权测试

## P1：工具与上下文

- 将 `retrieve_knowledge`、`find_questions`、`search_learning_resources` 作为正式 Tool 注册
- 由资源顾问 Agent 真正选择工具并返回结构化结果
- 使用模型 Tokenizer 控制上下文预算
- 超长历史使用滚动摘要
- 加入工具调用次数、超时和重试策略

## P2：Agent Middleware

- 模型路由：小模型处理结构化和短任务
- 模型回退：主模型超时后切换备用模型
- 输出修复：结构化输出失败时有限重试
- 安全中间件：Prompt 注入检测、PII 脱敏
- Trace：节点、Tool、Token、成本和错误记录

## P3：高级 RAG

- Query Rewrite、多查询检索
- 向量与关键词 RRF 融合
- Reranker
- 文档上传、解析、切分和增量索引
- 引用、召回率、MRR、nDCG 与端到端事实性评测

## P4：MCP 与多智能体

- 先把题库检索和知识检索封装成 MCP Server
- 再通过 MCP Client 接入外部工具
- 仅在收益明确时拆分 Interviewer、Evaluator、Coach Agent
- 多 Agent 必须有 Supervisor、Handoff Schema、共享状态和终止条件

