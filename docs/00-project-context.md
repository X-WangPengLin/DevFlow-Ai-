# 项目上下文

更新：2026-11-18。设计基线为同目录中的原始总体设计与 PNG/SVG 架构图。原始设计描述目标状态；本文件记录实际状态。

## 当前进度

M0 工程初始化已落地。M1 的基础知识检索链路已实现：知识库、Markdown/PDF 上传、结构切分、Ollama 本地向量、pgvector Dense 检索、基于检索片段的引用回答、失败状态与重试。真实 NGINX、Docker 和 Kubernetes 文档已入库；浏览器中已验证 Docker PDF 问答。当前有 28 份有效文档、839 个片段，其中 27 份 Markdown 固定到官方仓库提交号，Docker PDF 由官方 URL 与 SHA-256 固定；839 个片段均能按原文位置反查。50 道候选题已有待审核队列，人工审核数为 0，M1 尚未完整验收。

2026-11-17 新增引用原文定位：后端按 Markdown 全文或 PDF 指定页返回提取文本及哈希；前端引用卡片核对哈希与字符范围后高亮原文上下文。真实 API 已分别在 NGINX Markdown 和 Docker PDF 上验证位置一致；前端类型检查与生产构建通过。本次浏览器自动化超时，新增按钮的点击交互尚未完成浏览器验收。

已新增 `/knowledge/test` M1 验收页：实时显示 API/数据库状态及所选知识库文档数，直接运行 Dense Top-5 检索和引用回答，展示来源、片段、原文定位及浏览器端耗时。页面不提供模拟数据，也不计算正式质量指标。真实 HTTP 链路已验证页面 200、健康接口 200、检索返回 5 条、Docker 问答返回 1 条引用；浏览器点击验收仍待完成。

2026-11-18 验收页增加 Ollama 模型状态与一键真实链路检查。一次检查包含 Docker PDF、NGINX Markdown 的检索/原文/回答，以及无证据问题的拒答。实际检查发现 Docker 问题曾给出正确命令却引用 Kubernetes；回答链路现对明确提及的单一产品限定证据，并验证回答中的 `docker`/`kubectl`/`nginx` 命令出现在被引片段。真实 Docker、NGINX 和拒答请求复测通过。该命令校验只是有限的规则，生成文本的完整忠实度仍需人工审核。

## 技术决策

- 模块化单体：前端 `apps/web`，后端 `services/api`，本地数据库 `infra`。
- Python 限定 3.12；项目根目录 `.env` 为本地配置，`.env.example` 为无真实凭据示例。
- `/health` 只检查 API；`/health/db` 进行真实 `SELECT 1`。首页健康标识指向 `/health`。
- `/health/models` 读取本机 Ollama 已安装模型列表，显示当前配置的 Embedding 与聊天模型是否存在；实际推理由检索和问答请求验证。
- `0002_knowledge` 迁移建立知识库、文档和 2560 维向量片段表；`0003_source_spans` 增加原文字符范围。Markdown 使用换行符统一后的文本偏移，PDF 使用 pypdf 逐页抽取文本的页内偏移；原件哈希用于发现源文件变化。Embedding 模型固定 `qwen3-embedding:4b`；聊天模型使用本机 `qwen3:8b`。
- 本机已有 PostgreSQL 使用 5432，DevFlow 容器映射到本机 5433。
- Kubernetes 文档使用官方网站 `kubernetes/website` 的 `release-1.36` 提交 `1de955ebabe7e17da1ebb4f582635491227f4157`，入库时标记产品版本 `1.36`；原文只存在 Git 忽略目录，来源与许可记录在 `datasets/m1-sources.json`。
- `datasets/m1-sources.json` 与哈希清单覆盖全部 28 份有效文档；`import_sources.py` 可在本地 API 和数据库健康时统一重建，审核队列也可从该清单重新生成。Docker PDF 的官方 URL 非提交固定地址，若远端内容改变，导入会因 SHA-256 不一致而停止。
- 知识库入口已开放；故障诊断和检索实验室仍显示“规划中”。

## 运行方式

见根目录 `README.md`。核心顺序：启动 Docker 数据库、`uv sync`、`alembic upgrade head`、启动 Uvicorn、`pnpm install`、启动 Next.js。

## 待办

- M1 剩余：补充 Spring Boot 等语料并处理其官方 AsciiDoc 格式；人工核对现有 50 道候选题及证据，冻结测试集后形成正式质量基线；人工审核生成回答对证据的忠实度。当前候选正例在真实 Top-5 中为 42/48 命中，6 道未命中须分析。`datasets/m1-review-queue.csv` 中 50 条均为 `pending`，不能视为已审核。
- 后续在网络稳定时复核一次全新目录中的 `pnpm install --frozen-lockfile`；本机已完成安装、启动、检查和构建，初次下载因 npm 镜像连接不稳定使用官方 tarball 的本地缓存完成。
