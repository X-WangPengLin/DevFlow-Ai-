"use client";

import { useEffect, useState } from "react";
import { CitationView, type Citation } from "@/components/citation-view";

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type Base = { id: number; name: string };
type Doc = { id: string; filename: string; status: string; error: string | null; chunk_count: number; product: string | null; product_version: string | null };
type Answer = { answer: string; citations: Citation[]; answerable: boolean };

export default function KnowledgePage() {
  const [bases, setBases] = useState<Base[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [newName, setNewName] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${api}${path}`, options);
    if (!response.ok) throw new Error(`请求失败（${response.status}）：${await response.text()}`);
    return response.json();
  }
  async function refreshBases() {
    const data = await request<Base[]>("/api/knowledge-bases");
    setBases(data);
    setSelected((current) => current ?? data[0]?.id ?? null);
  }
  async function refreshDocs(id: number) { setDocuments(await request<Doc[]>(`/api/knowledge-bases/${id}/documents`)); }
  useEffect(() => { refreshBases().catch((e: Error) => setError(e.message)); }, []);
  useEffect(() => { if (selected !== null) refreshDocs(selected).catch((e: Error) => setError(e.message)); }, [selected]);

  async function createBase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    try {
      const item = await request<Base>("/api/knowledge-bases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName }) });
      await refreshBases(); setSelected(item.id); setNewName("");
    } catch (e) { setError((e as Error).message); }
  }
  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (selected === null) return;
    setBusy(true); setError("");
    const form = event.currentTarget;
    try {
      const body = new FormData(form);
      await request(`/api/knowledge-bases/${selected}/documents`, { method: "POST", body });
      await refreshDocs(selected); form.reset();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function ask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (selected === null) return;
    setBusy(true); setError(""); setResult(null);
    try { setResult(await request<Answer>(`/api/knowledge-bases/${selected}/answer`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function retry(id: string) {
    if (selected === null) return;
    setBusy(true); setError("");
    try { await request(`/api/documents/${id}/retry`, { method: "POST" }); await refreshDocs(selected); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <main className="workspace"><header className="workspace-header"><a href="/">← DevFlow RAG</a><a href="/knowledge/test">打开 M1 验收台 ↗</a></header><div className="workspace-intro"><span className="section-kicker">KNOWLEDGE WORKSPACE</span><h1>知识库与引用问答</h1><p>上传真实技术文档，从原文中检索证据。故障诊断与检索实验室仍在规划中。</p></div>
    {error && <div className="notice error" role="alert">{error}</div>}
    <div className="workspace-grid"><section className="panel"><h2>知识库</h2><form onSubmit={createBase} className="row"><input aria-label="知识库名称" placeholder="新知识库名称" value={newName} onChange={(e) => setNewName(e.target.value)} required /><button>创建</button></form><label>当前知识库<select value={selected ?? ""} onChange={(e) => setSelected(Number(e.target.value))}>{bases.map((base) => <option key={base.id} value={base.id}>{base.name}</option>)}</select></label>
      {selected !== null && <><h2>导入文档</h2><form onSubmit={upload} className="stack"><input type="file" name="file" accept=".md,.pdf" required /><input name="source_url" type="url" placeholder="来源 URL（可选）" /><input name="product" placeholder="产品（可选）" /><input name="product_version" placeholder="版本（可选）" /><button disabled={busy}>{busy ? "处理中…" : "上传并建立索引"}</button></form><p className="hint">支持 UTF-8 Markdown / PDF，最大 10 MB；原件保存在本机。</p></>}
      <h2>文档状态</h2>{documents.length ? <ul className="document-list">{documents.map((doc) => <li key={doc.id}><strong>{doc.filename}</strong><span>{doc.status === "ready" ? `已索引 · ${doc.chunk_count} 段` : doc.status === "failed" ? `失败：${doc.error}` : "处理中"}</span><small>{[doc.product, doc.product_version].filter(Boolean).join(" · ")}</small>{doc.status === "failed" && <button type="button" disabled={busy} onClick={() => retry(doc.id)}>重试索引</button>}</li>)}</ul> : <p className="hint">尚无文档。</p>}</section>
      <section className="panel"><h2>提问</h2><form onSubmit={ask} className="stack"><textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="例如：连接被拒绝时应检查什么？" required minLength={2} /><button disabled={busy || selected === null}>{busy ? "检索中…" : "检索并回答"}</button></form>{result && <div className="answer"><h3>回答</h3><p>{result.answer}</p>{result.citations.length > 0 && <><h3>引用原文</h3>{result.citations.map((cite) => <CitationView key={`${cite.document_id}-${cite.source_start}-${cite.number}`} cite={cite} api={api} />)}</>}</div>}</section></div></main>;
}
