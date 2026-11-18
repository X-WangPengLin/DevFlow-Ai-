# M1 评测题人工审核

`datasets/m1-review-queue.csv` 是待审核工作表，不是标准答案集。当前 50 条均为 `pending`，其中 48 条指定证据、2 条预期无法回答。题目由现有语料编制，候选 Top-5 为 42/48 命中；该结果有选择偏差，6 条未命中须逐题检查。增添语料会使原先的负例失效，已因此更换过一条 Kubernetes 驱逐负例。

## 审核步骤

1. 对每道题独立阅读原始文档，核实问题表述、产品/版本、`answerable` 和证据。正例核对 `source_url`、`source_sha256`、PDF 页码与 `source_start` / `source_end` 指向的文本。Markdown 偏移基于统一换行符后的文本；PDF 偏移基于 pypdf 提取的页内文本，不是纸面坐标。`match_count` 大于 1 时尤其要确认所选位置。
2. 负例检查当前知识库的覆盖范围，确认它确实没有可支持的答案；新增语料后必须重新审查负例。
3. 修正错误标注后将 `review_status` 改为 `approved`，填写真实 `reviewer` 和 ISO 日期时间 `reviewed_at`，并在 `review_notes` 记录歧义或修正依据。仍有争议的条目保持 `pending`，弃用条目设为 `rejected`。
4. 至少 50 道题经人工审核后固定 CSV、语料清单、文件哈希、嵌入模型与索引版本。后端目录运行 `uv run python evaluate_m1.py <知识库ID> --reviewed`。脚本会核对题数、审核字段、来源哈希、原文范围，再用真实 API 计算正例证据 Recall@5 和负例正确拒答率。生成答案的忠实度仍需另外逐条人工判读。

不要重新运行 `prepare_review_queue.py` 来修改已有审核表；脚本在输出文件存在时会拒绝覆盖。需要增加题目时，在已核验的现有 CSV 中添加新行，并赋予唯一 ID。仅填写审核字段不能替代真实人工复核。
