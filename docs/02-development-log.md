# 开发日志

## 2026-11-04 — M0 工程初始化

- 开始前：当前绝对路径 `/Users/wangpenglin/Desktop/DevFlow-Ai`，非 iCloud Drive 路径；根目录仅有原始设计 Markdown 和 PNG/SVG 架构图，无 `.git`。远端 `main` 为单次提交、仅含初始 README。
- 通过 `git init`、`fetch`、跟踪远端 `main` 接入既有历史；未覆盖原始文件、未推送。
- 原始三份资料保留在根目录，并复制到 `docs/`。原始设计提到的 `.mmd` 文件不存在。
- 环境：Node 20.13.1、pnpm 11.25.0、系统 Python 3.9.6、uv 0.12.1、uv 管理的 Python 3.12.13、Docker 29.5.3、Compose 5.1.4。Docker 服务起初未运行，随后启动 Docker Desktop。
- 实现：Next.js 首页、规划中入口、API 健康显示；FastAPI 路由、配置、CORS、异常处理；SQLAlchemy、pgvector 容器、Alembic 扩展迁移。

## 验收记录

- `uv sync --python 3.12` 成功，使用 Python 3.12.13；`uv run pytest -q`：3 passed，其中 `test_database_health_with_real_postgres` 查询真实容器。
- `./dev.sh` 启动成功；真实 HTTP 请求 `GET /health` 和 `GET /health/db` 均返回 200、`{"status":"ok"}`。
- `docker compose -f infra/docker-compose.yml up -d --wait` 成功，PostgreSQL 17.11 容器健康；使用本机 5433，避免占用现有 5432。
- `uv run alembic upgrade head` 成功；`uv run alembic current` 为 `0001_enable_vector (head)`；容器内查询到 `vector|0.8.7` 及版本表 `0001_enable_vector`。
- Alembic 离线 SQL 也已生成，但不作为在线迁移的替代证据。
- `pnpm-lock.yaml` 已生成。npm 与镜像站下载多次超时；通过下载并校验官方 Next.js 15.5.28 tarball、临时本地缓存安装完成前端依赖。最终 `package.json` 与锁文件均已恢复为可移植的 registry 依赖声明；全新目录下的冻结锁文件安装尚未复核。
- `pnpm check:web` 成功；`pnpm build:web` 成功，首页静态生成。修正 CSS `align-items` 兼容性警告后重跑构建，无该警告。
- `pnpm dev:web` 启动成功；真实 HTTP 请求首页返回 200。浏览器中确认导航、三个“规划中”入口、移动布局与“后端在线”状态。后端状态来自实际 `/health` 请求。
- Git 状态检查已执行；未跟踪内容包含开发前已有的三份原始资料及本次新增工程文件，另有 README 修改。原始资料仍在根目录。
- `git diff --check` 通过；`main` 跟踪 `origin/main`，远端最新历史仍是 `7deaa66 Initial commit`，未提交或推送。

## 2026-11-13 — M1 基础知识检索链路（进行中）

- 开发前检查：`main` 仍跟踪 `origin/main`，M0 文件尚未提交；保留全部现有修改。Docker 起初未运行，启动后 PostgreSQL 容器健康。
- 本机 Ollama 已有 `qwen3-embedding:4b` 和 `qwen3:8b`；真实 `/api/embed` 返回 2560 维向量。没有使用 API Key。
- 新增 `0002_knowledge` 在线迁移：知识库、文档和向量片段表。接口包括知识库创建/列表、Markdown/PDF 上传、文档状态与原文件、失败重试、Dense 检索和带引用回答。
- 下载 NGINX 官方 `Configuring Logging` Markdown 到 Git 忽略的 `data/samples`，来源为 `https://github.com/nginx/documentation/blob/main/content/nginx/admin-guide/monitoring/logging.md`；未将第三方全文加入仓库。
- 真实接口验证：创建知识库 ID 1；该文档上传后状态 `ready`、21 个片段。提问“NGINX 错误日志如何查看，默认路径是什么？”得到 `logs/error.log`、`/var/log/nginx/error.log` 和 `nginx -V`，引用命中原文 `Default path` 章节，相似度 0.7948。无关的量子计算机问题返回证据不足、空引用。
- 上传无效 PDF 后记录 `failed` 与解析错误；重试接口保持失败并返回错误，未伪装为成功。
- M1 尚未完成：PDF 正常文件的端到端验证、多文档来源/版本固定、约 50 道人工审核问题及检索质量基线。生成答案的事实忠实度仍需人工评审。
- 恢复开发后重新验收：`uv run pytest -q` 为 3 passed；`uv run alembic current` 为 `0002_knowledge (head)`；真实数据库现有 1 个知识库、2 条文档记录（其中一条无效 PDF 为失败样例）、21 个片段。`/health/db` 返回 200。
- 数据库端口改为仅绑定 `127.0.0.1:5433`，Compose 重建容器后数据仍在且健康。
- npm 下载再次不稳定：从官方版本对应 tarball 校验 SHA-512 后临时本地安装 Next.js 15.5.28；`pnpm check:web` 与 `pnpm build:web` 均通过，构建包含 `/knowledge`。页面 HTTP 请求返回 200。随后恢复 `package.json` 和 `pnpm-lock.yaml` 的常规 registry 声明；全新目录冻结锁文件安装仍未验证。
- 浏览器自动化打开工作台时超时，未完成点击上传/问答的浏览器交互验收；真实后端 HTTP 链路与前端构建分别验证，不将其表述为浏览器端到端联调。
- `git diff --check` 通过；原有未提交文件和 Git 历史保留，未执行 push。

## 2026-11-13 — M1 PDF 与浏览器验收

- 下载 Docker 官方 CLI Cheat Sheet PDF（`https://docs.docker.com/get-started/docker_cheatsheet.pdf`）到 Git 忽略的 `data/samples`，未将第三方全文加入仓库。PDF 为 1 页，pypdf 实际抽取 2938 个字符。
- 通过真实上传接口入库，状态 `ready`，切分为 3 段；数据库原有 NGINX Markdown 21 段仍在。失败 PDF 样例保留为 `failed` 状态，用于核对失败展示。
- 浏览器知识库页面显示 3 个文档状态。页面提问“如何列出本地 Docker 镜像？”返回 `docker images [1]`，引用指向 Docker PDF 第 1 页，检索相似度 0.6334；原文件接口已改为 `inline`，响应头核对为 `application/pdf`。
- 新增 8 道候选题（6 道有指定片段、2 道无答案）及最小评测脚本。真实 Top-5 检查为 6/6 找到指定片段；语料仅 2 份，且人工审核数为 0，不能将 100% 当作正式检索质量指标。无答案问题的生成拒答还需更大语料验证。
- 两份有效文档同时在库时，Kubernetes Pod 驱逐策略问题实际返回证据不足且无引用；这只覆盖该单题。
- 修改后复核：前端 TypeScript 检查与 Next.js 生产构建通过；后端 pytest 3 passed，Alembic 为 `0002_knowledge (head)`；`git diff --check` 通过。
- 下一步：扩大合法来源且版本明确的语料，人工核对约 50 道问题和稳定原文跨度，冻结测试集后再运行正式基线。

## 2026-11-13 — M1 固定来源语料扩充

- 读取 NGINX `nginx/documentation` 的 `6a3949a5536baed5c12e3c25083e66a4e566781e` 与 Docker `docker/docs` 的 `a0442378fca4987b1235614ec917b4138b5d5e5d` 提交，选取 18 份官方 Markdown。来源与提交号在 `datasets/m1-sources.json`，下载文件哈希在 `datasets/m1-corpus-manifest.json`；第三方全文仅在 Git 忽略的 `data/samples/pinned`。
- 18/18 份新增文档真实上传成功、状态 `ready`，新增 388 个片段。数据库共 20 份有效文档、412 个片段；另有 1 份此前的无效 PDF 保留 `failed` 状态。
- 后端按知识库、文件名和 SHA-256 对已就绪文档去重；重复上传原有 NGINX 文档及重复运行 18 份导入均未增加文档数。清单与本地文件哈希逐一核对 18/18 通过。
- 扩充候选题至 26 道（24 道有指定原文片段、2 道无答案）。首次检查 23/24，发现一题把 Markdown 标题当作正文片段；修正候选标注后重跑为 24/24 Top-5 命中。该集按当前语料编制，人工审核数为 0，结果不能用于宣称泛化性能。
- 在扩容语料上，关于 NGINX `Connection refused` 的真实回答引用了错误日志与调试文档；回答忠实度仍需人工核对。
- 可复现命令：后端目录运行 `uv run python import_sources.py 1`、`uv run python evaluate_m1.py 1`。

## 2026-11-13 — M1 原文位置与审核队列

- 开发前复核 `main...origin/main`、原始设计、架构图和现有上下文；保留原有未提交工作，未推送。
- 新增 `0003_source_spans` 在线迁移及回填脚本；412/412 个现有片段均获得原文字符范围。逐片读取 Git 忽略的原文件并反查内容，412/412 精确一致。新文档入库也会写入位置；检索响应增加 SHA-256、页码与偏移。
- 生成 `datasets/m1-review-queue.csv`：26 条全部 `pending`，24 正例、2 负例。正例记录来源 URL、SHA-256、页码与证据原文范围；生成脚本拒绝覆盖已有审核表。
- `evaluate_m1.py --reviewed` 要求至少 50 条审核通过且有审核人/时间，并核对来源哈希和原文范围。实际执行被正确拒绝：`Formal baseline requires 50 approved questions; found 0`。因此没有正式质量指标。
- 真实 API 候选 Top-5 再次检查为 24/24 命中，但题目按当前语料选取且无人审核，仅作开发诊断。真实 PostgreSQL `/health/db` 返回 200；`uv run alembic current` 为 `0003_source_spans (head)`；`uv run pytest -q` 为 3 passed，另有 Starlette/httpx 弃用警告。
- 尚需扩充跨产品语料、约 50 条人工审核题和生成回答忠实度审核。原文偏移仅是文本位置，不是 PDF 页面坐标；它不能代替人工确认引用所支持的结论。

## 2026-11-13 — M1 Kubernetes 1.36 语料扩充

- 开发前检查 `main...origin/main`、未提交改动、原始设计、项目上下文与架构图；保留原文件及 Git 历史，没有推送。
- 从 Kubernetes 官方 `kubernetes/website` 的 `release-1.36` 固定提交 `1de955ebabe7e17da1ebb4f582635491227f4157` 取得 8 篇 Markdown，记录路径、来源 URL、许可、取得日期、字节数和 SHA-256。正文留在 Git 忽略的 `data/samples/pinned`。导入脚本新增 `product_version` 上传字段，并在任何导入失败时返回非零状态。
- 8/8 篇通过真实 FastAPI 上传接口入库并标记 `ready`，产品版本为 `1.36`。数据库现有 28 份有效文档、839 个片段；逐片从原文偏移反查，839/839 内容精确一致；8 份新文档的存储文件哈希与清单一致。
- 候选题扩至 50 道（48 正例、2 负例），审核表 50 条仍全为 `pending`。原来的 Kubernetes 驱逐负例因新增文档失效，替换为当前语料未覆盖的 PostgreSQL 18 问题；两道负例真实回答均拒答且无引用。
- 真实 Top-5 候选检查为 42/48 正例命中。未命中 6 道涉及 Deployment 发布状态/扩缩容、Service EndpointSlice、Ready 状态等；题目由当前语料编制且未经人工审核，不能作为正式检索质量指标，也不应把未命中改写成命中。
- 真实 Kubernetes 问答“容器上次崩溃前的日志如何查看？”返回 `kubectl logs ${POD_NAME} -c ${CONTAINER_NAME} --previous` 并引用 `kubernetes-debug-running-pod.md`。这是 API 联调，未声称浏览器端到端验收或逐条答案忠实度审核。
- 复核 `uv run pytest -q` 为 3 passed，真实数据库 `/health/db` 可用，迁移为 `0003_source_spans (head)`。Spring Boot 官方参考文档以 AsciiDoc 为主，目前没有引入未经核对的转换内容。

## 2026-11-13 — M1 语料导入与审核队列复现

- 开发前复核 Git 状态、原始设计、上下文与架构文档；保留原有未提交文件及历史，未推送。
- 将单独上传的 NGINX logging Markdown 和 Docker CLI Cheat Sheet PDF 加入来源与哈希清单。前者从 NGINX 官方仓库已有固定提交重新下载，后者从 Docker 官方 PDF 地址重新下载；两者分别与本地原件的 SHA-256 完全一致。导入脚本现在支持清单中的官方直链与 PDF 文件类型。
- 首次重跑时本地 API 进程已退出，28 项均报告连接失败且脚本以非零状态结束；重新启动 API 后重跑，28/28 项返回 `ready`。新增启动前 API/数据库健康检查，避免服务未运行时逐项失败。重复导入后知识库仍为 28 份有效文档、839 个片段，没有重复记录。
- 审核队列生成脚本统一读取 28 份文件的清单并校验哈希；在临时目录重新生成 50 条队列，与现有队列逐字段完全一致。现有队列仍全为 `pending`，不构成正式评测基线。
- 对 6 道候选 Top-5 漏召回题扩展只读检索到 Top-50，指定证据均存在于索引中：M1-033 排名 14、M1-034 排名 16、M1-036 排名 8、M1-037 排名 8、M1-038 排名 11、M1-049 排名 19。Top-5 多次出现同一文档的其他片段；这是当前 Dense 排名与片段粒度下的观察，尚未做人工相关性复核或 M2 策略实验。

## 2026-11-17 — M1 引用原文定位

- 开发前检查 Git 状态、上下文、架构与原始总体设计；保留未提交改动，不推送。
- 新增 `GET /api/documents/{id}/text`，返回规范化 Markdown 原文或 PDF 指定页提取文本；读取时校验原件 SHA-256，页码不合法时返回 400。前端引用卡片增加“查看原文位置”，核对响应哈希及字符范围与当前引用一致后显示高亮上下文。
- 真实 API 对 NGINX logging Markdown 和 Docker CLI PDF 第 1 页分别验证：返回文本按 `source_start:source_end` 截取后与检索片段完全一致。后端 `uv run pytest -q` 为 3 passed，数据库健康；前端 TypeScript 检查与 Next.js 15.5.28 生产构建通过，`next start` 已启动。
- npm 下载不稳定导致普通 pnpm 检查尝试重新下载 Next.js；使用此前保存的官方 tarball，并核对其 SHA-512 与现有锁文件一致，临时本地安装后完成检查和构建，随后恢复原 `package.json` 与 `pnpm-lock.yaml`。浏览器自动化两次超时，新增按钮的点击流程未验证；不将接口与构建检查描述成浏览器联调。

## 2026-11-17 — M1 前端验收页

- 开发前检查 Git 状态、项目上下文、架构及原始总体设计，保留现有未提交文件。
- 新增 `/knowledge/test` 页面并从首页及知识库工作台提供入口。页面实时读取 API/数据库健康、知识库与文档状态，分别运行真实 Dense Top-5 检索和引用回答，复用原文定位卡片，并显示浏览器端耗时；示例问题不会伪装成测试结果。
- 前端 TypeScript 检查及 Next.js 生产构建通过，构建包含 `/knowledge/test`。后端 pytest 3 passed。真实 HTTP 请求：页面 200，`/health` 和 `/health/db` 均 200，当前知识库文档列表 29 条（28 ready、1 failed），Docker 问题检索返回 5 条，回答返回 1 条引用。浏览器交互尚未完成自动化验收。

## 2026-11-18 — M1 模型状态与引用校验

- 开发前复核 Git 状态、项目上下文、架构、原始设计，保留未提交改动。
- 新增 `/health/models` 读取本机 Ollama `/api/tags`；真实接口返回 `qwen3-embedding:4b`、`qwen3:8b` 均已安装。验收页增加模型状态与一键冒烟检查，逐项请求真实 Top-5、原文位置、引用回答和无证据拒答；缺少样本文件时显示跳过。
- 冒烟检查的前置真实请求暴露 Docker 问题错误引用 Kubernetes 文档的情况。后端回答现从 Dense Top-20 中筛选问题明确提及的单一产品，再取 Top-5 作为上下文；命令行回答若含 `docker`、`kubectl`、`nginx` 命令，要求命令文本出现在被引片段，否则拒答。该规则不能替代完整人工忠实度审核。
- 真实 API 复测：Docker 问题引用 `docker_cheatsheet.pdf`，NGINX 问题引用 `nginx-logging.md`，量子计算机问题拒答且无引用。另加 2 个使用模拟检索/模型输出的单元测试保护错引拒答和产品限定；这两个测试不是前后端真实联调证据。浏览器控制工具仍超时，页面点击未完成自动化验证。
- 最终复核：后端 `uv run pytest -q` 为 5 passed（含上述 2 个模拟单元测试），前端 TypeScript 与生产构建通过。按验收页一键检查的相同顺序实际请求 API，Docker PDF、NGINX Markdown、负例拒答 3 项均通过；这是 HTTP 链路验收，浏览器点击状态仍未验证。
