import { HealthStatus } from "../components/health-status";

const features = [
  { id: "knowledge", number: "01", title: "知识库", description: "导入 Markdown 或 PDF，检索文档证据并查看引用回答。", milestone: "M1" },
  { id: "diagnosis", number: "02", title: "故障诊断", description: "结合故障描述和文档证据，整理候选原因与人工排查步骤。", milestone: "M3" },
  { id: "playground", number: "03", title: "检索实验室", description: "对比检索候选、引用与耗时，定位检索质量问题。", milestone: "M2" },
];

export default function Home() {
  return <div className="site-shell">
    <header className="site-header"><a className="brand" href="#top"><span className="brand-mark">D<span>.</span></span><span>DevFlow <b>RAG</b></span></a><nav aria-label="主导航"><a href="/knowledge">知识库</a><a href="/knowledge/test">M1 验收台</a><a href="#diagnosis">故障诊断</a><a href="#playground">检索实验室</a></nav><HealthStatus /></header>
    <main id="top">
      <section className="hero"><div className="eyebrow"><span className="eyebrow-line" /> ENGINEERING INTELLIGENCE / M1</div><h1>让每一次故障排查<br /><em>都有据可循。</em></h1><p>面向开发与运维工程师的技术知识检索平台。从可信文档出发，逐步构建可追溯的故障诊断工作流。</p><a className="hero-link" href="#modules">探索功能模块 <span aria-hidden="true">↗</span></a><div className="hero-aside">当前阶段 <strong>M1 · 基础知识检索</strong><span>知识库已开放，诊断功能仍在规划中</span></div></section>
      <section id="modules" className="modules"><div className="section-head"><div><span className="section-kicker">PLATFORM MODULES</span><h2>从知识到判断</h2></div><p>知识库现已开放；其他模块随里程碑逐步上线。</p></div><div className="feature-grid">{features.map((feature) => <article className="feature-card" id={feature.id} key={feature.id}><div className="card-top"><span>{feature.number} / 03</span><span className="badge">{feature.id === "knowledge" ? "已开放" : `规划中 · ${feature.milestone}`}</span></div><div className="card-icon" aria-hidden="true">{feature.number === "01" ? "▤" : feature.number === "02" ? "◇" : "⌁"}</div><h3>{feature.title}</h3><p>{feature.description}</p><div className="card-foot">{feature.id === "knowledge" ? <a href="/knowledge">进入知识库 ↗</a> : "尚未开放"}</div></article>)}</div></section>
    </main><footer><span>DevFlow RAG</span><span>技术故障知识检索与智能诊断平台 · M1 进行中</span></footer>
  </div>;
}
