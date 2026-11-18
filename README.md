# DevFlow RAG

面向技术故障知识检索与智能诊断的模块化单体项目。当前已具备 **M1 基础知识检索链路**：Markdown/PDF 上传、切分、Ollama Embedding、pgvector Dense 检索和带原文引用的回答。故障诊断与检索实验室仍在规划中。

## 环境准备

- macOS、Node.js 20.9+、pnpm 11、Python 3.12、uv、Docker Desktop、Ollama。
- 在 Ollama 中准备 `qwen3-embedding:4b` 和 `qwen3:8b`（`ollama pull`）；可以用 `.env` 修改模型名，但向量维度目前固定为 2560。
- 项目放在 Mac 本地目录，避免 iCloud Drive 同步开发目录。
- 从项目根目录执行 `cp .env.example .env`，本地开发可先使用示例值。`.env` 已被 Git 忽略。数据库默认映射到本机 5433，避免占用已有的 5432；远程部署时必须更换数据库密码。

## 启动

```sh
# 项目根目录：数据库
docker compose -f infra/docker-compose.yml up -d --wait

# 后端依赖与迁移
cd services/api
uv sync --python 3.12
uv run alembic upgrade head
./dev.sh

# 另一个终端，项目根目录：前端
pnpm install
pnpm dev:web
```

浏览器打开 <http://localhost:3000>，API 文档在 <http://localhost:8000/docs>。`GET /health` 检查 API 进程；`GET /health/db` 真实查询数据库。前端健康标识只反映 API 进程状态。

知识库工作台在 <http://localhost:3000/knowledge>。先创建知识库，再上传 UTF-8 Markdown 或 PDF；文件上限 10 MB，处理结果会显示 `ready` 或失败原因。提问时使用真实向量检索及本地模型回答，并提供原文件与章节/页码引用。原文件保存在被 Git 忽略的 `data/uploads`。上传的文档和提问会传给本机 Ollama。

引用卡片中的“查看原文位置”会读取保留的 Markdown 文本或 PDF 指定页文本，并用来源哈希与字符范围核对片段后高亮上下文。PDF 原文件链接仍以页码打开；字符范围是提取文本的位置，并非 PDF 版面坐标。

M1 人工验收页：<http://localhost:3000/knowledge/test>。启动前后端后，选择知识库，确认 API、数据库、Ollama 模型状态与已索引文档数；可点击“一键冒烟检查”运行两道有证据问题和一道无证据问题，也可手动点击“运行 Dense Top-5 检索”和“生成引用回答”，检查真实来源、拒答行为以及“查看原文位置”。页面的示例问题只提供输入建议，所有结果取自当前数据库和模型；页面不输出正式评测分数。

小规模开发检查可在后端目录执行 `uv run python evaluate_m1.py 1`。它读取 `datasets/m1-candidate-questions.jsonl`，检查 Top-5 是否包含指定原文片段。题目是候选集，尚未经过人工审核，不能作为正式检索质量结论。

`datasets/m1-review-queue.csv` 有 50 道待人工审核的候选题，包含来源哈希与原文字符范围。审核方法见 [评测审核说明](docs/04-evaluation-review.md)。后端目录的 `uv run python evaluate_m1.py 1 --reviewed` 只接受至少 50 道带审核人和时间的 `approved` 题；目前会明确拒绝运行正式基线。新增 Kubernetes 1.36 官方文档后，候选正例的真实 Top-5 检查为 42/48，另有 2 道负例；这些都不是正式质量指标。已有数据从迁移 `0003_source_spans` 升级后，执行 `PYTHONPATH=src uv run python backfill_source_spans.py` 回填原文位置；新入库文档自动记录该位置。

`datasets/m1-sources.json` 覆盖全部 28 份 NGINX/Docker/Kubernetes 官方样本：27 份 Markdown 固定到仓库提交，Docker CLI Cheat Sheet PDF 使用官方直链；`datasets/m1-corpus-manifest.json` 固定每份文件哈希。Kubernetes 资料固定在 1.36 文档分支的提交，并记录 CC BY 4.0 来源许可。后端目录执行 `uv run python import_sources.py <知识库ID>`，脚本先检查本地 API/数据库，再下载文档到 Git 忽略的 `data/samples/pinned`，核对哈希后通过 API 入库。重复导入同一文件会复用现有记录；如果官方 PDF 内容改变，哈希校验会停止导入。

## 验证

```sh
pnpm check:web
pnpm build:web
cd services/api && uv run pytest
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/health/db
```

数据库扩展验证：`docker compose -f infra/docker-compose.yml exec db psql -U devflow -d devflow -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"`

## 工程结构

- `apps/web`：Next.js 首页与知识库工作台。
- `services/api`：FastAPI、文档入库/检索/回答、配置、数据库连接、迁移和测试。
- `infra`：本地 PostgreSQL + pgvector。
- `docs`：原始设计资料、架构说明、开发日志与路线图。

设计基线见 [项目总体设计](docs/DevFlow-RAG-%E9%A1%B9%E7%9B%AE%E6%80%BB%E4%BD%93%E8%AE%BE%E8%AE%A1.md)。运行与验收现状见 [项目上下文](docs/00-project-context.md) 和 [开发日志](docs/02-development-log.md)。
