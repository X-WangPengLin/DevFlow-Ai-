"use client";

import { useEffect, useState } from "react";
import { CitationView, type Citation } from "@/components/citation-view";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type Base = { id: number; name: string };
type Doc = { id: string; filename: string; status: string; chunk_count: number };
type Hit = Omit<Citation, "number"> & { chunk_id: number };
type Answer = { answer: string; citations: Citation[]; answerable: boolean };
type Health = "检查中" | "正常" | "不可用";
type ModelHealth = { status: "ok" | "missing"; embedding_model: string; embedding_ready: boolean; chat_model: string; chat_ready: boolean };
type SmokeResult = { name: string; status: "通过" | "未通过" | "跳过"; detail: string };

const examples = [
  "如何查看本地 Docker 镜像？",
  "NGINX 默认错误日志在哪里？",
  "如何修理量子计算机冷却系统？",
];

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${api}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(`${path} 返回 ${response.status}：${await response.text()}`);
  return response.json();
}

export default function KnowledgeTestPage() {
  const [apiHealth, setApiHealth] = useState<Health>("检查中");
  const [dbHealth, setDbHealth] = useState<Health>("检查中");
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [modelStatus, setModelStatus] = useState<Health>("检查中");
  const [bases, setBases] = useState<Base[]>([]);
  const [baseId, setBaseId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [question, setQuestion] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [searchMs, setSearchMs] = useState<number | null>(null);
  const [answerMs, setAnswerMs] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [smoke, setSmoke] = useState<SmokeResult[]>([]);

  async function checkServices() {
    setApiHealth("检查中"); setDbHealth("检查中"); setModelStatus("检查中"); setError("");
    const [apiResult, dbResult, modelResult, baseResult] = await Promise.allSettled([
      getJson<{ status: string }>("/health"),
      getJson<{ status: string }>("/health/db"),
      getJson<ModelHealth>("/health/models"),
      getJson<Base[]>("/api/knowledge-bases"),
    ]);
    setApiHealth(apiResult.status === "fulfilled" && apiResult.value.status === "ok" ? "正常" : "不可用");
    setDbHealth(dbResult.status === "fulfilled" && dbResult.value.status === "ok" ? "正常" : "不可用");
    setModelHealth(modelResult.status === "fulfilled" ? modelResult.value : null);
    setModelStatus(modelResult.status === "fulfilled" && modelResult.value.status === "ok" ? "正常" : "不可用");
    if (baseResult.status === "fulfilled") {
      setBases(baseResult.value);
      setBaseId((current) => baseResult.value.some((base) => base.id === current) ? current : baseResult.value[0]?.id ?? null);
    } else { setError(baseResult.reason instanceof Error ? baseResult.reason.message : "知识库列表读取失败"); }
  }

  useEffect(() => { void checkServices(); }, []);
  useEffect(() => {
    setHits(null); setAnswer(null); setSearchMs(null); setAnswerMs(null); setSmoke([]);
    if (baseId === null) { setDocuments([]); return; }
    getJson<Doc[]>(`/api/knowledge-bases/${baseId}/documents`).then(setDocuments).catch((cause: Error) => setError(cause.message));
  }, [baseId]);

  async function run(path: "search" | "answer") {
    if (baseId === null || question.trim().length < 2) return;
    setBusy(true); setError("");
    if (path === "search") { setHits(null); setSearchMs(null); }
    else { setAnswer(null); setAnswerMs(null); }
    const started = performance.now();
    try {
      const result = await getJson<Hit[] | Answer>(`/api/knowledge-bases/${baseId}/${path}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question.trim() }),
      });
      const elapsed = Math.round(performance.now() - started);
      if (path === "search") { setHits(result as Hit[]); setSearchMs(elapsed); }
      else { setAnswer(result as Answer); setAnswerMs(elapsed); }
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }

  async function runSmoke() {
    if (baseId === null) return;
    setBusy(true); setError(""); setSmoke([]);
    const results: SmokeResult[] = [];
    const positiveCases = [
      { name: "Docker PDF 检索、引用与原文", question: "如何查看本地 Docker 镜像？", filename: "docker_cheatsheet.pdf", evidence: "docker images" },
      { name: "NGINX Markdown 检索、引用与原文", question: "NGINX 默认错误日志在哪里？", filename: "nginx-logging.md", evidence: "logs/error.log" },
    ];
    for (const item of positiveCases) {
      if (!ready.some((doc) => doc.filename === item.filename)) {
        results.push({ name: item.name, status: "跳过", detail: `当前知识库没有 ${item.filename}` });
        setSmoke([...results]);
        continue;
      }
      try {
        const hits = await getJson<Hit[]>(`/api/knowledge-bases/${baseId}/search`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: item.question }),
        });
        const hit = hits.find((candidate) => candidate.filename === item.filename && candidate.excerpt.includes(item.evidence));
        if (!hit) throw new Error("Top-5 未找到指定文件及证据");
        const source = await getJson<{ text: string; sha256: string }>(`/api/documents/${hit.document_id}/text${hit.page ? `?page=${hit.page}` : ""}`);
        if (source.sha256 !== hit.sha256 || hit.source_start === null || hit.source_end === null ||
            source.text.slice(hit.source_start, hit.source_end) !== hit.excerpt) throw new Error("原文哈希或片段位置不一致");
        const response = await getJson<Answer>(`/api/knowledge-bases/${baseId}/answer`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: item.question }),
        });
        if (!response.answerable || !response.citations.some((cite) => cite.filename === item.filename)) {
          throw new Error("回答没有引用指定文件");
        }
        results.push({ name: item.name, status: "通过", detail: `Top-5 命中，原文位置一致，回答引用 ${item.filename}` });
      } catch (cause) {
        results.push({ name: item.name, status: "未通过", detail: (cause as Error).message });
      }
      setSmoke([...results]);
    }
    try {
      const response = await getJson<Answer>(`/api/knowledge-bases/${baseId}/answer`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: "如何修理量子计算机冷却系统？" }),
      });
      results.push(response.answerable || response.citations.length ?
        { name: "无证据问题拒答", status: "未通过", detail: `answerable=${response.answerable}，引用 ${response.citations.length} 条` } :
        { name: "无证据问题拒答", status: "通过", detail: "明确拒答且没有引用" });
    } catch (cause) { results.push({ name: "无证据问题拒答", status: "未通过", detail: (cause as Error).message }); }
    setSmoke([...results]); setBusy(false);
  }

  const ready = documents.filter((doc) => doc.status === "ready");
  const failed = documents.filter((doc) => doc.status === "failed");

  return <main className="workspace test-workspace">
    <header className="workspace-header"><a href="/knowledge">← 知识库</a><a href="/knowledge/review">人工审核评测题 ↗</a></header>
    <div className="workspace-intro"><span className="section-kicker">LIVE ACCEPTANCE</span><h1>M1 验收台</h1><p>页面直接调用当前本机 API 和知识库。示例问题只是输入建议；请按实际返回的文档和原文判断结果。</p></div>
    <div className="test-status-grid">
      <section className="panel"><h2>服务状态</h2><p>API：<strong>{apiHealth}</strong></p><p>PostgreSQL：<strong>{dbHealth}</strong></p><p>本地模型：<strong>{modelStatus}</strong></p>{modelHealth && <p className="hint">Embedding {modelHealth.embedding_model}：{modelHealth.embedding_ready ? "已安装" : "缺失"}<br />Chat {modelHealth.chat_model}：{modelHealth.chat_ready ? "已安装" : "缺失"}</p>}<button type="button" onClick={() => void checkServices()}>重新检查</button><p className="hint">分别读取 /health、/health/db 与 /health/models；模型状态仅检查已安装，实际推理由下方请求验证。</p></section>
      <section className="panel"><h2>语料状态</h2><label>知识库<select value={baseId ?? ""} disabled={busy} onChange={(event) => setBaseId(Number(event.target.value))}>{bases.map((base) => <option key={base.id} value={base.id}>{base.name}</option>)}</select></label><p>已索引：<strong>{ready.length}</strong> 份 · <strong>{ready.reduce((sum, doc) => sum + doc.chunk_count, 0)}</strong> 段</p><p>失败：<strong>{failed.length}</strong> 份</p><p className="hint">来自所选知识库的实时文档列表。</p></section>
    </div>
    {error && <div className="notice error" role="alert">{error}</div>}
    <section className="panel smoke-panel"><h2>一键冒烟检查</h2><p>对所选知识库运行两道有证据问题和一道无证据问题，逐项检查 Top-5、原文位置、回答引用与拒答。结果只用于本机功能验收。</p><button type="button" disabled={busy || baseId === null || apiHealth !== "正常" || dbHealth !== "正常" || modelStatus !== "正常"} onClick={() => void runSmoke()}>{busy ? "检查中…" : "运行真实链路检查"}</button>{smoke.length > 0 && <ol className="smoke-results">{smoke.map((item) => <li key={item.name}><strong>{item.status}</strong><span>{item.name}</span><small>{item.detail}</small></li>)}</ol>}</section>
    <section className="panel test-query"><h2>真实检索与问答</h2><label>问题<textarea value={question} onChange={(event) => { setQuestion(event.target.value); setHits(null); setAnswer(null); setSearchMs(null); setAnswerMs(null); }} placeholder="输入技术问题" minLength={2} /></label><div className="test-examples">{examples.map((example) => <button type="button" key={example} onClick={() => { setQuestion(example); setHits(null); setAnswer(null); setSearchMs(null); setAnswerMs(null); }}>{example}</button>)}</div><div className="test-actions"><button type="button" disabled={busy || baseId === null || question.trim().length < 2} onClick={() => void run("search")}>运行 Dense Top-5 检索</button><button type="button" disabled={busy || baseId === null || question.trim().length < 2} onClick={() => void run("answer")}>生成引用回答</button></div><p className="hint">检索和回答分别发起真实请求；耗时为浏览器端观测值。这里不计算正式评测指标。</p></section>
    <div className="test-results">
      <section className="panel"><h2>检索结果 {searchMs !== null && <small>· {searchMs} ms</small>}</h2>{hits === null ? <p className="hint">尚未运行检索。</p> : hits.length === 0 ? <p>没有检索到片段。</p> : hits.map((hit, index) => <CitationView key={`${hit.chunk_id ?? index}-${index}`} cite={{ ...hit, number: index + 1 }} api={api} />)}</section>
      <section className="panel"><h2>回答结果 {answerMs !== null && <small>· {answerMs} ms</small>}</h2>{answer === null ? <p className="hint">尚未生成回答。</p> : <><p className="test-answer-state">{answer.answerable ? "有引用回答" : "证据不足，已拒答"} · {answer.citations.length} 条引用</p><p className="answer">{answer.answer}</p>{answer.citations.map((cite) => <CitationView key={`${cite.document_id}-${cite.source_start}-${cite.number}`} cite={cite} api={api} />)}</>}</section>
    </div>
  </main>;
}
