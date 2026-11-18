"""Run a small candidate retrieval check against the live M1 API.

These questions are agent prepared candidates, not human reviewed gold labels.
"""
import json
import csv
import hashlib
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader


API = "http://127.0.0.1:8000"
DATASET = Path(__file__).resolve().parents[2] / "datasets/m1-candidate-questions.jsonl"
REVIEWED = Path(__file__).resolve().parents[2] / "datasets/m1-review-queue.csv"
ROOT = Path(__file__).resolve().parents[2]


def validate_reviewed(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    approved = [row for row in rows if row["review_status"] == "approved"]
    if len(approved) < 50:
        raise ValueError(f"Formal baseline requires 50 approved questions; found {len(approved)}")
    if any(not row["reviewer"].strip() or not row["reviewed_at"].strip() for row in approved):
        raise ValueError("Each approved question needs reviewer and reviewed_at")
    if len({row["id"] for row in approved}) != len(approved):
        raise ValueError("Duplicate review IDs")
    positives = [row for row in approved if row["answerable"] == "true"]
    negatives = [row for row in approved if row["answerable"] == "false"]
    if len(positives) + len(negatives) != len(approved) or not positives or not negatives:
        raise ValueError("Approved questions need valid answerable labels of both types")
    for row in positives:
        filename = row["filename"]
        if Path(filename).name != filename:
            raise ValueError(f"Invalid filename in {row['id']}")
        paths = [ROOT / "data/samples" / filename, ROOT / "data/samples/pinned" / filename]
        path = next((candidate for candidate in paths if candidate.is_file()), None)
        if path is None:
            raise ValueError(f"Source file missing for {row['id']}: {filename}")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != row["source_sha256"]:
            raise ValueError(f"Source hash changed for {row['id']}")
        if path.suffix.lower() == ".pdf":
            pages = PdfReader(path).pages
            page = int(row["page"])
            if page < 1 or page > len(pages):
                raise ValueError(f"Invalid page for {row['id']}")
            source_text = pages[page - 1].extract_text() or ""
        else:
            if row["page"]:
                raise ValueError(f"Markdown source must not have a page for {row['id']}")
            source_text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        start, end = int(row["source_start"]), int(row["source_end"])
        if start < 0 or end <= start or end > len(source_text) or source_text[start:end].lower() != row["evidence"].lower():
            raise ValueError(f"Evidence span no longer matches source for {row['id']}")
    return positives, negatives


def post(path: str, payload: dict) -> object:
    request = Request(API + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def main(base_id: int, reviewed: bool = False) -> None:
    if reviewed:
        with REVIEWED.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        try:
            positives, negatives = validate_reviewed(rows)
        except (ValueError, KeyError) as exc:
            raise SystemExit(str(exc)) from exc
        matched = 0
        for row in positives:
            hits = post(f"/api/knowledge-bases/{base_id}/search", {"question": row["question"]})
            found = any(hit["filename"] == row["filename"] and hit["sha256"] == row["source_sha256"]
                        and (not row["page"] or hit["page"] == int(row["page"]))
                        and hit["source_start"] is not None
                        and hit["source_start"] < int(row["source_end"])
                        and hit["source_end"] > int(row["source_start"]) for hit in hits)
            matched += found
            print(json.dumps({"id": row["id"], "hit_at_5": found}, ensure_ascii=False))
        refused = 0
        for row in negatives:
            response = post(f"/api/knowledge-bases/{base_id}/answer", {"question": row["question"]})
            refused += not response["answerable"] and not response["citations"]
        print(json.dumps({"reviewed": len(positives) + len(negatives), "evidence_recall_at_5": matched / len(positives),
                          "correct_refusal_rate": refused / len(negatives), "positive_questions": len(positives),
                          "negative_questions": len(negatives)}, ensure_ascii=False))
        return
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    matches = 0
    positive = 0
    for row in rows:
        if not row["answerable"]:
            continue
        positive += 1
        hits = post(f"/api/knowledge-bases/{base_id}/search", {"question": row["question"]})
        found = any(hit["filename"] == row["filename"] and row["evidence"].lower() in hit["excerpt"].lower() for hit in hits)
        matches += found
        print(json.dumps({"question": row["question"], "hit_at_5": found, "top_filename": hits[0]["filename"] if hits else None}, ensure_ascii=False))
    print(json.dumps({"candidate_evidence_recall_at_5": matches / positive if positive else None,
                      "matched": matches, "positive_questions": positive, "total_candidates": len(rows),
                      "human_reviewed": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1, "--reviewed" in sys.argv)
