"use client";

import { useEffect, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Question = {
  id: string; question: string; answerable: string; filename: string; source_url: string;
  source_sha256: string; page: string; source_start: string; source_end: string;
  evidence: string; match_count: string; review_status: string; reviewer: string;
  reviewed_at: string; review_notes: string; document_id: string | null;
};
type Source = { text: string; sha256: string };
type Base = { id: number; name: string };
type Retrieval = { evidence_rank: number | null; top5: { filename: string; heading: string | null; score: number; excerpt: string; matches_candidate: boolean }[] };

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${api}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status}：${await response.text()}`);
  return response.json();
}

export default function ReviewPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [filter, setFilter] = useState("all");
  const [source, setSource] = useState<Source | null>(null);
  const [sourceError, setSourceError] = useState("");
  const [bases, setBases] = useState<Base[]>([]);
  const [baseId, setBaseId] = useState<number | null>(null);
  const [retrieval, setRetrieval] = useState<Retrieval | null>(null);
  const [retrievalBusy, setRetrievalBusy] = useState(false);
  const [status, setStatus] = useState("pending");
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [verified, setVerified] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([json<Question[]>("/api/evaluation/questions"), json<Base[]>("/api/knowledge-bases")])
      .then(([rows, items]) => { setQuestions(rows); setSelectedId(rows[0]?.id ?? ""); setBases(items); setBaseId(items[0]?.id ?? null); })
      .catch((cause: Error) => setError(cause.message));
  }, []);

  const selected = questions.find((item) => item.id === selectedId);
  useEffect(() => {
    setStatus(selected?.review_status ?? "pending");
    setReviewer(selected?.reviewer ?? ""); setNotes(selected?.review_notes ?? "");
    setVerified(false); setSource(null); setSourceError(""); setRetrieval(null); setMessage("");
    if (!selected || selected.answerable !== "true") return;
    if (!selected.document_id) { setSourceError("当前知识库中没有匹配文件及哈希的原件。"); return; }
    const page = selected.page ? `?page=${selected.page}` : "";
    json<Source>(`/api/documents/${selected.document_id}/text${page}`)
      .then(setSource).catch((cause: Error) => setSourceError(cause.message));
  }, [selectedId, selected?.document_id]);

  const filtered = questions.filter((item) => filter === "all" || item.review_status === filter);
  const pending = questions.filter((item) => item.review_status === "pending").length;
  const approved = questions.filter((item) => item.review_status === "approved").length;
  const rejected = questions.filter((item) => item.review_status === "rejected").length;
  const start = Number(selected?.source_start);
  const end = Number(selected?.source_end);
  const sourceValid = !!selected && !!source && source.sha256 === selected.source_sha256 &&
    Number.isInteger(start) && Number.isInteger(end) && start >= 0 && end > start &&
    source.text.slice(start, end).toLowerCase() === selected.evidence.toLowerCase();
  const contextStart = sourceValid ? Math.max(0, start - 320) : 0;
  const contextEnd = sourceValid ? Math.min(source!.text.length, end + 320) : 0;

  async function checkRetrieval() {
    if (!selected || baseId === null) return;
    setRetrievalBusy(true); setRetrieval(null); setError("");
    try { setRetrieval(await json<Retrieval>(`/api/evaluation/questions/${selected.id}/retrieval?base_id=${baseId}`)); }
    catch (cause) { setError((cause as Error).message); }
    finally { setRetrievalBusy(false); }
  }

  async function save() {
    if (!selected) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const updated = await json<Question>(`/api/evaluation/questions/${selected.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reviewer, notes, verified }),
      });
      setQuestions((rows) => rows.map((item) => item.id === selected.id ? { ...item, ...updated } : item));
      setMessage(`${selected.id} 已保存到审核 CSV。`);
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }

  return <main className="workspace review-workspace">
    <header className="workspace-header"><a href="/knowledge/test">← M1 验收台</a><span>评测题人工审核</span></header>
    <div className="workspace-intro"><span className="section-kicker">M1 REVIEW QUEUE</span><h1>逐题核对证据</h1><p>审核结果直接保存到版本化 CSV。请阅读原文并判断题目、证据和可回答性；页面的哈希与位置校验不能替代人工判断。</p></div>
    <div className="review-summary"><strong>{questions.length} 道候选题</strong><span>待审核 {pending}</span><span>已通过 {approved}</span><span>已退回 {rejected}</span></div>
    {error && <div className="notice error" role="alert">{error}</div>}
    {message && <div className="notice success" role="status">{message}</div>}
    <div className="review-grid">
      <section className="panel review-list"><h2>题目列表</h2><label>状态筛选<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">全部</option><option value="pending">待审核</option><option value="approved">已通过</option><option value="rejected">已退回</option></select></label><ul>{filtered.map((item) => <li key={item.id}><button type="button" className={item.id === selectedId ? "selected" : ""} onClick={() => setSelectedId(item.id)}><small>{item.id} · {item.review_status === "approved" ? "已通过" : item.review_status === "rejected" ? "已退回" : "待审核"}</small><span>{item.question}</span></button></li>)}</ul></section>
      <section className="panel review-detail">{selected ? <>
        <div className="review-title"><span className="section-kicker">{selected.id}</span><h2>{selected.question}</h2><p>{selected.answerable === "true" ? "候选标注：可回答" : "候选标注：无法回答"} · {selected.filename || "无指定文件"}</p></div>
        {selected.answerable === "true" ? <>
          <dl className="review-meta"><div><dt>来源</dt><dd><a href={selected.source_url} target="_blank" rel="noreferrer">打开来源网页 ↗</a></dd></div><div><dt>位置</dt><dd>{selected.page ? `PDF 第 ${selected.page} 页` : "Markdown 原文"} · 字符 {selected.source_start}–{selected.source_end}</dd></div><div><dt>候选证据</dt><dd><code>{selected.evidence}</code>（原文匹配 {selected.match_count} 处）</dd></div></dl>
          {sourceError && <p className="source-error">{sourceError}</p>}
          {source && (sourceValid ? <div className="review-source" aria-label="原文上下文"><p>原件哈希与证据范围校验通过，请继续判断证据是否支持问题。</p><pre>{source.text.slice(contextStart, start)}<mark>{source.text.slice(start, end)}</mark>{source.text.slice(end, contextEnd)}</pre></div> : <p className="source-error">原件哈希或证据范围不一致，请勿通过该题。</p>)}
        </> : <div className="review-source"><p>无答案候选题：请检查当前语料覆盖范围，确认没有足以支持答案的文档。新增语料后需要重新审核。</p></div>}
        <div className="review-retrieval"><h3>实时检索诊断</h3><label>知识库<select value={baseId ?? ""} onChange={(event) => { setBaseId(Number(event.target.value)); setRetrieval(null); }}>{bases.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button type="button" disabled={baseId === null || retrievalBusy} onClick={() => void checkRetrieval()}>{retrievalBusy ? "检索中…" : "检查证据排名"}</button><p className="hint">查询真实 Dense Top-50，显示候选证据首次出现的位置；这是开发诊断，不是正式质量指标。</p>{retrieval && <><p className="review-rank">{selected.answerable === "true" ? retrieval.evidence_rank === null ? "候选证据未进入 Top-50" : `候选证据排名第 ${retrieval.evidence_rank} 位${retrieval.evidence_rank <= 5 ? " · Top-5 命中" : " · Top-5 未命中"}` : "无答案候选题：以下结果仍需人工判断能否支持答案"}</p><ol>{retrieval.top5.map((hit, index) => <li key={`${hit.filename}-${index}`}><strong>{hit.filename}</strong> · {hit.score}{hit.matches_candidate && " · 指定证据"}{hit.heading && <small>{hit.heading}</small>}<p>{hit.excerpt}</p></li>)}</ol></>}</div>
        <div className="review-form"><h3>记录人工审核</h3><label>审核状态<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="pending">待审核</option><option value="approved">通过</option><option value="rejected">退回</option></select></label><label>审核人<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="填写真实审核人" /></label><label>审核备注<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="记录歧义、修正依据或退回原因" /></label><label className="review-confirm"><input type="checkbox" checked={verified} onChange={(event) => setVerified(event.target.checked)} />我已人工核对题目与{selected.answerable === "true" ? "来源原文、可回答性" : "当前语料覆盖范围、可回答性"}</label><button type="button" disabled={busy || (status !== "pending" && (!reviewer.trim() || !verified || (selected.answerable === "true" && !sourceValid)))} onClick={() => void save()}>{busy ? "保存中…" : "保存审核结果"}</button><p className="hint">正例只有原文哈希与范围一致才能通过；题目或证据标注需要修正时先退回并写明原因。正式基线要求至少 50 道人工审核通过。</p></div>
      </> : <p className="hint">正在读取审核队列…</p>}</section>
    </div>
  </main>;
}
