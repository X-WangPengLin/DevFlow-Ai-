"use client";

import { useState } from "react";

export type Citation = {
  number: number; document_id: string; filename: string; source_url: string | null;
  heading: string | null; page: number | null; excerpt: string; score: number;
  sha256: string; source_start: number | null; source_end: number | null;
};

type SourceText = { text: string; sha256: string; page: number | null };

export function CitationView({ cite, api }: { cite: Citation; api: string }) {
  const [source, setSource] = useState<SourceText | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function showSource() {
    if (source) { setSource(null); return; }
    setLoading(true); setError("");
    try {
      const query = cite.page === null ? "" : `?page=${cite.page}`;
      const response = await fetch(`${api}/api/documents/${cite.document_id}/text${query}`);
      if (!response.ok) throw new Error(`原文读取失败（${response.status}）`);
      const data: SourceText = await response.json();
      if (data.sha256 !== cite.sha256 || cite.source_start === null || cite.source_end === null ||
          data.text.slice(cite.source_start, cite.source_end) !== cite.excerpt) {
        throw new Error("原文位置与当前引用不一致，请重新提问。");
      }
      setSource(data);
    } catch (cause) { setError((cause as Error).message); }
    finally { setLoading(false); }
  }

  const start = cite.source_start ?? 0;
  const end = cite.source_end ?? 0;
  const from = Math.max(0, start - 350);
  const to = source ? Math.min(source.text.length, end + 350) : 0;

  return <article className="citation">
    <a href={`${api}/api/documents/${cite.document_id}/file${cite.page ? `#page=${cite.page}` : ""}`} target="_blank" rel="noreferrer">[{cite.number}] {cite.filename} ↗</a>
    <small>{cite.heading && `章节：${cite.heading} `}{cite.page && `第 ${cite.page} 页`} · 相似度 {cite.score}{cite.source_url && <> · <a href={cite.source_url} target="_blank" rel="noreferrer">来源网页</a></>}</small>
    <blockquote>{cite.excerpt}</blockquote>
    <button className="source-toggle" type="button" onClick={showSource} disabled={loading}>{loading ? "读取中…" : source ? "收起原文位置" : "查看原文位置"}</button>
    {error && <p className="source-error" role="alert">{error}</p>}
    {source && <div className="source-context" aria-label={`${cite.filename} 原文位置`}><pre>{from > 0 && "…\n"}{source.text.slice(from, start)}<mark>{source.text.slice(start, end)}</mark>{source.text.slice(end, to)}{to < source.text.length && "\n…"}</pre></div>}
  </article>;
}
