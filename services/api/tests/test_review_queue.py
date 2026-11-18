import csv
from pathlib import Path

from fastapi.testclient import TestClient

from devflow_rag import review_queue
from devflow_rag.main import app


def test_review_queue_saves_pending_without_approving(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "review.csv"
    fields = ["id", "question", "answerable", "filename", "source_sha256", "page",
              "source_start", "source_end", "evidence", "review_status", "reviewer",
              "reviewed_at", "review_notes"]
    with queue.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"id": "M1-TEST", "question": "无法回答的问题", "answerable": "false",
                         "review_status": "pending"})
    monkeypatch.setattr(review_queue, "QUEUE", queue)
    client = TestClient(app)
    blocked = client.patch("/api/evaluation/questions/M1-TEST", json={
        "status": "approved", "reviewer": "Tester", "verified": False,
    })
    assert blocked.status_code == 422
    saved = client.patch("/api/evaluation/questions/M1-TEST", json={
        "status": "pending", "notes": "需要人工核对覆盖范围", "verified": False,
    })
    assert saved.status_code == 200
    assert saved.json()["review_status"] == "pending"
    with queue.open(encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["review_notes"] == "需要人工核对覆盖范围"
    assert row["reviewed_at"] == ""
