"""Local M1 question review queue. The CSV remains the versioned source of truth."""

import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from devflow_rag import knowledge


QUEUE = Path(__file__).resolve().parents[4] / "datasets/m1-review-queue.csv"
REQUIRED = {"id", "question", "answerable", "filename", "source_sha256", "page",
            "source_start", "source_end", "evidence", "review_status", "reviewer",
            "reviewed_at", "review_notes"}


def _read() -> tuple[list[str], list[dict[str, str]]]:
    try:
        with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            if not REQUIRED.issubset(fields):
                raise HTTPException(500, "Review queue columns are incomplete")
            return fields, list(reader)
    except FileNotFoundError as exc:
        raise HTTPException(503, "Review queue is unavailable") from exc


def list_questions() -> list[dict]:
    _, rows = _read()
    with knowledge.SessionLocal() as session:
        documents = session.scalars(select(knowledge.Document).where(knowledge.Document.status == "ready")).all()
    document_ids = {(doc.filename, doc.sha256): doc.id for doc in documents}
    return [{**row, "document_id": document_ids.get((row["filename"], row["source_sha256"]))}
            for row in rows]


def retrieval_check(question_id: str, base_id: int) -> dict:
    _, rows = _read()
    row = next((item for item in rows if item["id"] == question_id), None)
    if row is None:
        raise HTTPException(404, "Question not found")
    hits = knowledge.search(base_id, row["question"], limit=50)
    def matches(hit: dict) -> bool:
        return (row["answerable"] == "true" and hit["filename"] == row["filename"]
                and hit["sha256"] == row["source_sha256"]
                and (not row["page"] or hit["page"] == int(row["page"]))
                and hit["source_start"] is not None
                and hit["source_start"] < int(row["source_end"])
                and hit["source_end"] > int(row["source_start"]))
    rank = next((index for index, hit in enumerate(hits, 1) if matches(hit)), None)
    return {"question_id": question_id, "evidence_rank": rank,
            "top5": [{"filename": hit["filename"], "heading": hit["heading"],
                      "score": hit["score"], "excerpt": hit["excerpt"][:320],
                      "matches_candidate": matches(hit)} for hit in hits[:5]]}


def save_review(question_id: str, status: str, reviewer: str, notes: str, verified: bool) -> dict:
    fields, rows = _read()
    row = next((item for item in rows if item["id"] == question_id), None)
    if row is None:
        raise HTTPException(404, "Question not found")
    if status not in {"pending", "approved", "rejected"}:
        raise HTTPException(422, "Invalid review status")
    if status != "pending" and (not reviewer.strip() or not verified):
        raise HTTPException(422, "Reviewer and source verification are required")
    if status == "approved" and row["answerable"] == "true":
        matching = next((doc for doc in list_questions() if doc["id"] == question_id), None)
        if not matching or not matching["document_id"]:
            raise HTTPException(422, "Source document is missing")
        page = int(row["page"]) if row["page"] else None
        source = knowledge.source_text(matching["document_id"], page)
        start, end = int(row["source_start"]), int(row["source_end"])
        if source["sha256"] != row["source_sha256"] or start < 0 or end <= start or source["text"][start:end].lower() != row["evidence"].lower():
            raise HTTPException(422, "Evidence no longer matches source")
    row["review_status"] = status
    row["reviewer"] = reviewer.strip() if status != "pending" else ""
    row["reviewed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds") if status != "pending" else ""
    row["review_notes"] = notes.strip()
    fd, temp_name = tempfile.mkstemp(prefix=".m1-review-", suffix=".csv", dir=QUEUE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_name, QUEUE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return row
