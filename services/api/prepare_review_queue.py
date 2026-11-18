"""Create an unapproved human review queue with stable source spans."""
import csv
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "datasets/m1-candidate-questions.jsonl"
OUTPUT = ROOT / "datasets/m1-review-queue.csv"
MANIFEST = {row["filename"]: row for row in json.loads((ROOT / "datasets/m1-corpus-manifest.json").read_text())}
FIELDS = ["id", "question", "answerable", "filename", "source_url", "source_sha256", "page",
          "source_start", "source_end", "evidence", "match_count", "review_status", "reviewer", "reviewed_at", "review_notes"]


def source(filename: str) -> tuple[Path, str]:
    row = MANIFEST[filename]
    return ROOT / "data/samples/pinned" / filename, row["source_url"]


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Review queue already exists; preserve human edits: {OUTPUT}")
    rows = []
    for number, line in enumerate(QUESTIONS.read_text().splitlines(), 1):
        item = json.loads(line)
        record = dict.fromkeys(FIELDS, "")
        record.update(id=f"M1-{number:03}", question=item["question"], answerable=str(item["answerable"]).lower(),
                      filename=item["filename"] or "", evidence=item["evidence"] or "", review_status="pending")
        if item["answerable"]:
            path, url = source(item["filename"])
            data = path.read_bytes()
            checksum = hashlib.sha256(data).hexdigest()
            if checksum != MANIFEST[item["filename"]]["sha256"]:
                raise ValueError(f"Source hash changed: {item['filename']}")
            texts = ([page.extract_text() or "" for page in PdfReader(path).pages] if path.suffix == ".pdf"
                     else [data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")])
            matches = [(page_no, text.lower().find(item["evidence"].lower()), text.lower().count(item["evidence"].lower()))
                       for page_no, text in enumerate(texts, 1)]
            matches = [(page_no, start, count) for page_no, start, count in matches if start >= 0]
            if not matches:
                raise ValueError(f"Evidence not found: {item['question']}")
            page_no, start, _ = matches[0]
            record.update(source_url=url, source_sha256=checksum,
                          page=page_no if path.suffix == ".pdf" else "", source_start=start,
                          source_end=start + len(item["evidence"]), match_count=sum(count for _, _, count in matches))
        rows.append(record)
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"prepared {len(rows)} pending review rows: {OUTPUT}")


if __name__ == "__main__":
    main()
