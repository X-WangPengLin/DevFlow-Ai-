# 系统架构：M1 当前落地状态

总体目标参见 [原始设计](DevFlow-RAG-%E9%A1%B9%E7%9B%AE%E6%80%BB%E4%BD%93%E8%AE%BE%E8%AE%A1.md) 和 [架构图 SVG](DevFlow-RAG-总体架构图.svg)。图中多数模块为后续里程碑规划，不代表 M0 已实现。原始设计提及的 `.mmd` 文件不在本次收到的资料中；保留现有 SVG 作为可编辑来源。

```text
浏览器 → Next.js 知识库工作台 → FastAPI
                                 上传 → Markdown/PDF 解析 → Chunk → Ollama Embedding
                                                        → SQLAlchemy → PostgreSQL + pgvector
                                 提问 → Ollama Embedding → Dense Top-K → Ollama 回答 + 原文引用
Alembic → PostgreSQL（vector 扩展、知识库/文档/片段表、片段原文偏移）
```

## 代码边界

- `apps/web/src/app`：首页、知识库工作台和 `/knowledge/test` M1 验收页；`components/health-status.tsx`：真实 API 状态读取。验收页复用引用卡片，直接读取现有健康、文档、Dense 检索和回答接口。
- `/knowledge/review`：M1 人工审核工作台，读取版本化 CSV 候选题，调用原文接口展示证据上下文，保存人工审核状态、审核人和备注。
- `services/api/src/devflow_rag/api`：路由；`core/config.py`：环境配置；`core/database.py`：连接与基础会话；`main.py`：应用、中间件与异常处理。
- `services/api/src/devflow_rag/knowledge.py`：入库、切分、向量化、检索与回答。
- `GET /api/documents/{id}/text`：从保留原件读取规范化 Markdown 文本或指定 PDF 页文本，并核对原件哈希；引用卡片按片段偏移核对后高亮上下文。
- `GET /health/models`：检查 Ollama 已安装模型；验收页一键检查调用真实检索、回答和原文接口。回答链路对明确提及的单一产品只使用对应产品片段，并对常见命令进行引用文本核对。
- Dense 检索对问题中唯一明确提及且知识库中存在的产品先做数据库过滤，再按向量距离取 Top-K；多产品或未提及产品的问题保持跨产品检索。审核页的 `GET /api/evaluation/questions/{id}/retrieval?base_id=...` 只读查询真实 Top-50，报告候选证据排名和 Top-5 片段，用于开发诊断。
- 用户检索及候选 Recall@5 仍按 Dense Top-5；回答链路为寻找直接证据读取 Dense Top-20，并在返回引用前检查引用编号与常见命令文本。它不能自动验证所有自然语言结论，生成忠实度需人工审核。
- `services/api/alembic`：扩展与知识表迁移；`infra/docker-compose.yml`：本地数据库。
- `services/api/src/devflow_rag/review_queue.py`：读取和原子更新 `datasets/m1-review-queue.csv`；审核正例时再核对数据库原件的 SHA-256 和文本范围。`GET/PATCH /api/evaluation/questions` 提供本机审核接口，没有引入评测数据库表。

## 未来演进

M1 基础链路已实现，浏览器中已验证 PDF 的页码引用；`datasets/m1-sources.json` 记录全部 28 份 NGINX、Docker、Kubernetes 官方资料，`datasets/m1-corpus-manifest.json` 固定文件哈希。27 份 Markdown 使用仓库固定提交，Docker PDF 使用官方 URL 加文件哈希。导入脚本先检查本地 API 与数据库，再下载、核对哈希并通过真实上传接口入库；重复运行复用已有文档。Kubernetes 8 篇取自 `release-1.36` 的固定提交，入库时携带产品版本。`0003_source_spans` 与回填脚本使片段带原文偏移，检索响应包含文件哈希、页码和偏移；偏移指向规范化 Markdown 文本或 pypdf 提取的 PDF 页内文本，不等于 PDF 版面坐标。`datasets/m1-review-queue.csv` 保存 50 道待审核问题的原文证据位置；正式评测脚本拒绝少于 50 道审核通过的题。Spring Boot 官方参考资料主要为 AsciiDoc，本阶段尚未入库。仍需人工标注和正式质量评测。M2 增加 BM25/RRF/Rerank 和实验台；M3 增加双通道诊断；M4 完善评测、权限与可观测性。按需求增添代码模块，不预建空包。
