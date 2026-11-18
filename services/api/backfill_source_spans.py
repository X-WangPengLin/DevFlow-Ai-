"""Locate existing chunk text within retained original documents after migration 0003."""
from pathlib import Path

from sqlalchemy import select

from devflow_rag.core.database import SessionLocal
from devflow_rag.knowledge import Chunk, Document, _locate_parts


def main() -> None:
    updated = 0
    with SessionLocal.begin() as session:
        for doc in session.scalars(select(Document).where(Document.status == "ready")):
            chunks = session.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.ordinal)).all()
            if not chunks or all(chunk.source_start is not None for chunk in chunks):
                continue
            data = Path(doc.stored_path).read_bytes()
            parts = [(chunk.heading, chunk.page, chunk.content) for chunk in chunks]
            for chunk, (start, end) in zip(chunks, _locate_parts(doc.filename, data, parts)):
                chunk.source_start, chunk.source_end = start, end
                updated += 1
    print(f"backfilled {updated} chunk spans")


if __name__ == "__main__":
    main()
