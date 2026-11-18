import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pgvector.sqlalchemy import Vector
from pypdf import PdfReader
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from devflow_rag.core.config import get_settings
from devflow_rag.core.database import Base, SessionLocal


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    product: Mapped[str | None] = mapped_column(String(120))
    product_version: Mapped[str | None] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64))
    stored_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="processing")
    error: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    chunks: Mapped[list["Chunk"]] = relationship(cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(255))
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    source_start: Mapped[int | None] = mapped_column(Integer)
    source_end: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector(2560))


def _ollama(path: str, payload: dict) -> dict:
    settings = get_settings()
    request = Request(
        f"{settings.ollama_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def model_status() -> dict:
    settings = get_settings()
    try:
        with urlopen(f"{settings.ollama_url.rstrip('/')}/api/tags", timeout=5) as response:
            installed = {item["name"] for item in json.load(response).get("models", [])}
    except (OSError, URLError, ValueError) as exc:
        raise HTTPException(503, "Ollama unavailable") from exc
    embedding_ready = settings.embedding_model in installed
    chat_ready = settings.chat_model in installed
    return {"status": "ok" if embedding_ready and chat_ready else "missing",
            "embedding_model": settings.embedding_model, "embedding_ready": embedding_ready,
            "chat_model": settings.chat_model, "chat_ready": chat_ready}


def _embed(texts: list[str]) -> list[list[float]]:
    response = _ollama("/api/embed", {"model": get_settings().embedding_model, "input": texts})
    vectors = response["embeddings"]
    if len(vectors) != len(texts) or any(len(vector) != 2560 for vector in vectors):
        raise ValueError("Embedding dimensions did not match the database schema")
    return vectors


def _sections(filename: str, data: bytes) -> list[tuple[str | None, int | None, str]]:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 100:
            raise ValueError("PDF exceeds 100 pages")
        return [(None, i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    text = data.decode("utf-8")
    sections: list[tuple[str | None, int | None, str]] = []
    heading: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if body:
                sections.append((heading, None, "\n".join(body)))
            heading, body = line.lstrip("# ").strip(), []
        else:
            body.append(line)
    if body:
        sections.append((heading, None, "\n".join(body)))
    return sections


def _chunks(filename: str, data: bytes) -> list[tuple[str | None, int | None, str]]:
    result: list[tuple[str | None, int | None, str]] = []
    for heading, page, content in _sections(filename, data):
        content = content.strip()
        while content:
            if len(content) <= 1000:
                part, content = content, ""
            else:
                boundary = content.rfind("\n", 600, 1000)
                end = boundary if boundary > 0 else 1000
                part, content = content[:end], content[end:]
            if part.strip():
                result.append((heading, page, part.strip()))
            content = content.strip()
    return result


def _locate_parts(filename: str, data: bytes, parts: list[tuple[str | None, int | None, str]]) -> list[tuple[int, int]]:
    """Offsets use normalized Markdown text or pypdf text within each PDF page."""
    if filename.lower().endswith(".pdf"):
        pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages]
    else:
        pages = [data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")]
    offsets: list[tuple[int, int]] = []
    cursors: dict[int, int] = {}
    for _heading, page, content in parts:
        page_index = page - 1 if page is not None else 0
        text = pages[page_index]
        start = text.find(content, cursors.get(page_index, 0))
        if start < 0:
            raise ValueError("Could not locate a chunk in its original text")
        end = start + len(content)
        offsets.append((start, end))
        cursors[page_index] = end
    return offsets


def list_bases() -> list[dict]:
    with SessionLocal() as session:
        return [{"id": item.id, "name": item.name} for item in session.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id))]


def create_base(name: str) -> dict:
    if not name.strip():
        raise HTTPException(400, "Knowledge base name cannot be blank")
    with SessionLocal.begin() as session:
        item = KnowledgeBase(name=name.strip())
        session.add(item)
        session.flush()
        return {"id": item.id, "name": item.name}


def list_documents(base_id: int) -> list[dict]:
    with SessionLocal() as session:
        docs = session.scalars(select(Document).where(Document.knowledge_base_id == base_id).order_by(Document.created_at.desc())).all()
        return [document_dict(doc) for doc in docs]


def document_dict(doc: Document) -> dict:
    return {"id": doc.id, "filename": doc.filename, "status": doc.status, "error": doc.error,
            "source_url": doc.source_url, "product": doc.product, "product_version": doc.product_version,
            "sha256": doc.sha256, "embedding_model": doc.embedding_model,
            "chunk_count": len(doc.chunks)}


def get_document(doc_id: str) -> Document:
    with SessionLocal() as session:
        doc = session.get(Document, doc_id)
        if doc is None:
            raise HTTPException(404, "Document not found")
        session.expunge(doc)
        return doc


def source_text(doc_id: str, page: int | None) -> dict:
    doc = get_document(doc_id)
    data = Path(doc.stored_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != doc.sha256:
        raise HTTPException(409, "Original file no longer matches its indexed version")
    if doc.filename.lower().endswith(".pdf"):
        pages = PdfReader(io.BytesIO(data)).pages
        if page is None or page < 1 or page > len(pages):
            raise HTTPException(400, "A valid PDF page is required")
        text = pages[page - 1].extract_text() or ""
    else:
        if page is not None:
            raise HTTPException(400, "Markdown has no page number")
        text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return {"text": text, "sha256": doc.sha256, "page": page}


def ingest(base_id: int, filename: str, data: bytes, source_url: str | None, product: str | None, version: str | None) -> dict:
    settings = get_settings()
    if not filename.lower().endswith((".md", ".pdf")):
        raise HTTPException(400, "Only Markdown and PDF files are supported")
    if not data or len(data) > settings.max_upload_bytes:
        raise HTTPException(400, "File is empty or exceeds upload limit")
    safe_name = Path(filename).name
    checksum = hashlib.sha256(data).hexdigest()
    with SessionLocal() as session:
        duplicate = session.scalar(select(Document).where(Document.knowledge_base_id == base_id,
            Document.filename == safe_name, Document.sha256 == checksum, Document.status == "ready"))
        if duplicate is not None:
            return document_dict(duplicate)
    identifier = str(uuid.uuid4())
    folder = Path(settings.storage_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{identifier}{Path(safe_name).suffix.lower()}"
    with SessionLocal.begin() as session:
        if session.get(KnowledgeBase, base_id) is None:
            raise HTTPException(404, "Knowledge base not found")
        path.write_bytes(data)
        doc = Document(id=identifier, knowledge_base_id=base_id, filename=safe_name, source_url=source_url,
                       product=product, product_version=version, sha256=checksum,
                       stored_path=str(path), status="processing", embedding_model=settings.embedding_model)
        session.add(doc)
    _process(identifier, safe_name, data)
    with SessionLocal() as session:
        return document_dict(session.get(Document, identifier))


def _process(identifier: str, filename: str, data: bytes) -> None:
    try:
        parts = _chunks(filename, data)
        if not parts:
            raise ValueError("No extractable text found")
        offsets = _locate_parts(filename, data, parts)
        vectors = _embed([part[2] for part in parts])
        with SessionLocal.begin() as session:
            doc = session.get(Document, identifier)
            doc.chunks.clear()
            for ordinal, ((heading, page, content), embedding, (start, end)) in enumerate(zip(parts, vectors, offsets)):
                doc.chunks.append(Chunk(ordinal=ordinal, heading=heading, page=page, content=content,
                                        source_start=start, source_end=end, embedding=embedding))
            doc.status, doc.error = "ready", None
    except Exception as exc:
        with SessionLocal.begin() as session:
            doc = session.get(Document, identifier)
            doc.status, doc.error = "failed", str(exc)[:1000]


def retry_document(identifier: str) -> dict:
    with SessionLocal.begin() as session:
        doc = session.get(Document, identifier)
        if doc is None:
            raise HTTPException(404, "Document not found")
        if doc.status != "failed":
            raise HTTPException(409, "Only failed documents can be retried")
        filename, path = doc.filename, Path(doc.stored_path)
        doc.status, doc.error = "processing", None
    _process(identifier, filename, path.read_bytes())
    with SessionLocal() as session:
        return document_dict(session.get(Document, identifier))


def search(base_id: int, query: str, limit: int = 5) -> list[dict]:
    vector = _embed([query])[0]
    distance = Chunk.embedding.cosine_distance(vector)
    with SessionLocal() as session:
        products = session.scalars(select(Document.product).where(
            Document.knowledge_base_id == base_id, Document.status == "ready",
            Document.product.is_not(None)).distinct()).all()
        mentioned = [product for product in products if product and re.search(
            rf"(?<![A-Za-z0-9]){re.escape(product)}(?![A-Za-z0-9])", query, re.IGNORECASE)]
        statement = (select(Chunk, Document, distance.label("distance"))
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.knowledge_base_id == base_id, Document.status == "ready",
                   Document.embedding_model == get_settings().embedding_model))
        if len(mentioned) == 1:
            statement = statement.where(Document.product == mentioned[0])
        rows = session.execute(statement.order_by(distance).limit(limit)).all()
        return [{"chunk_id": chunk.id, "document_id": doc.id, "filename": doc.filename,
                 "source_url": doc.source_url, "sha256": doc.sha256, "product": doc.product, "product_version": doc.product_version,
                 "heading": chunk.heading, "page": chunk.page, "excerpt": chunk.content,
                 "source_start": chunk.source_start, "source_end": chunk.source_end,
                 "score": round(1 - float(d), 4)} for chunk, doc, d in rows]


def answer(base_id: int, question: str) -> dict:
    hits = search(base_id, question, limit=20)
    mentioned = {hit["product"].lower() for hit in hits if hit["product"] and hit["product"].lower() in question.lower()}
    if len(mentioned) == 1:
        hits = [hit for hit in hits if hit["product"] and hit["product"].lower() in mentioned]
    if not hits or hits[0]["score"] < get_settings().min_similarity:
        return {"answer": "当前知识库中没有足够证据回答这个问题。", "citations": [], "answerable": False}
    evidence = "\n\n".join(f"[{i}] 来源：{hit['filename']}\n{hit['excerpt']}" for i, hit in enumerate(hits, 1))
    prompt = ("只根据下列资料回答问题。不要使用外部知识，不要编造来源。若资料不足，请直接写‘证据不足’。"
              "优先找直接回答问题的原文，仔细区分肯定与否定语句，不要根据相似话题猜测结论。"
              "用简短中文回答；结论和每个命令必须由所引用的片段直接支持，引用资料时写 [1] 等对应编号。\n\n"
              + evidence + "\n\n问题：" + question)
    response = _ollama("/api/chat", {"model": get_settings().chat_model, "stream": False,
                                     "think": False, "messages": [{"role": "user", "content": prompt}]})
    content = response.get("message", {}).get("content", "").strip()
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", content)}
    valid = {n for n in cited if 1 <= n <= len(hits)}
    if not content or "证据不足" in content or not valid or valid != cited:
        return {"answer": "当前知识库中没有足够证据回答这个问题。", "citations": [], "answerable": False}
    cited_text = "\n".join(hits[n - 1]["excerpt"].lower() for n in valid)
    commands = {match.lower() for match in re.findall(r"\b(?:docker|kubectl|nginx)\s+[A-Za-z0-9_-]+", content)}
    if any(command not in cited_text for command in commands):
        return {"answer": "当前知识库中没有足够证据回答这个问题。", "citations": [], "answerable": False}
    return {"answer": content, "citations": [{"number": n, **hits[n-1]} for n in sorted(valid)], "answerable": True}
