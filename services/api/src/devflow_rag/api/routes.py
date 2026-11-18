from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from devflow_rag.core.database import check_database
from devflow_rag import knowledge

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def database_health() -> dict[str, str]:
    try:
        check_database()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}


@router.get("/health/models")
def models_health() -> dict:
    return knowledge.model_status()


class BaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class Query(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


@router.get("/api/knowledge-bases")
def list_bases() -> list[dict]:
    return knowledge.list_bases()


@router.post("/api/knowledge-bases", status_code=201)
def create_base(body: BaseCreate) -> dict:
    return knowledge.create_base(body.name)


@router.get("/api/knowledge-bases/{base_id}/documents")
def list_documents(base_id: int) -> list[dict]:
    return knowledge.list_documents(base_id)


@router.post("/api/knowledge-bases/{base_id}/documents", status_code=201)
async def upload_document(base_id: int, file: UploadFile = File(...), source_url: str | None = Form(None),
                          product: str | None = Form(None), product_version: str | None = Form(None)) -> dict:
    data = await file.read(knowledge.get_settings().max_upload_bytes + 1)
    return knowledge.ingest(base_id, file.filename or "", data, source_url, product, product_version)


@router.get("/api/documents/{document_id}")
def document_detail(document_id: str) -> dict:
    with knowledge.SessionLocal() as session:
        doc = session.get(knowledge.Document, document_id)
        if doc is None:
            raise HTTPException(404, "Document not found")
        return knowledge.document_dict(doc)


@router.get("/api/documents/{document_id}/file")
def original_file(document_id: str) -> FileResponse:
    doc = knowledge.get_document(document_id)
    return FileResponse(doc.stored_path, filename=doc.filename, content_disposition_type="inline")


@router.get("/api/documents/{document_id}/text")
def document_text(document_id: str, page: int | None = None) -> dict:
    return knowledge.source_text(document_id, page)


@router.post("/api/documents/{document_id}/retry")
def retry_document(document_id: str) -> dict:
    return knowledge.retry_document(document_id)


@router.post("/api/knowledge-bases/{base_id}/search")
def search(base_id: int, body: Query) -> list[dict]:
    return knowledge.search(base_id, body.question)


@router.post("/api/knowledge-bases/{base_id}/answer")
def answer(base_id: int, body: Query) -> dict:
    return knowledge.answer(base_id, body.question)
