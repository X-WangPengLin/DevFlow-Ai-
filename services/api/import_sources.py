"""Download pinned official sources locally and import through the live API.

Source bodies stay under the Git-ignored data/samples directory.
"""
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SOURCES = json.loads((ROOT / "datasets/m1-sources.json").read_text())
OUTPUT = ROOT / "data/samples/pinned"
API = "http://127.0.0.1:8000"
EXPECTED = {item["filename"]: item for item in json.loads((ROOT / "datasets/m1-corpus-manifest.json").read_text())}


def upload(base_id: int, name: str, data: bytes, source_url: str, product: str,
           product_version: str | None = None) -> dict:
    boundary = "devflowM1Boundary"
    fields = {"source_url": source_url, "product": product}
    if product_version:
        fields["product_version"] = product_version
    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    content_type = "application/pdf" if name.lower().endswith(".pdf") else "text/markdown"
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {content_type}\r\n\r\n".encode())
    body.extend(data)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    request = Request(f"{API}/api/knowledge-bases/{base_id}/documents", data=bytes(body),
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urlopen(request, timeout=300) as response:
        return json.load(response)


def main(base_id: int) -> None:
    try:
        with urlopen(f"{API}/health/db", timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"API health returned {response.status}")
    except Exception as exc:
        raise SystemExit(f"Local API or database is unavailable at {API}: {exc}") from exc
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for index, item in enumerate(SOURCES, 1):
        url = item.get("url") or f"https://raw.githubusercontent.com/{item['repository']}/{item['revision']}/{item['path']}"
        name = item.get("filename") or item["product"].lower() + "-" + Path(item["path"]).stem + ".md"
        local = OUTPUT / name
        if not local.exists():
            with urlopen(url, timeout=45) as response:
                local.write_bytes(response.read())
        data = local.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        expected = EXPECTED[name]
        if checksum != expected["sha256"] or len(data) != expected["bytes"]:
            raise ValueError(f"Source content differs from pinned manifest: {name}")
        try:
            result = upload(base_id, name, data, url, item["product"], item.get("product_version"))
            status = result["status"]
            chunks = result["chunk_count"]
        except Exception as exc:
            status, chunks = f"error: {exc}", 0
        record = {"filename": name, "source_url": url, "sha256": checksum, "bytes": len(data),
                  "status": status, "chunks": chunks}
        records.append(record)
        print(json.dumps({"index": index, **record}, ensure_ascii=False), flush=True)
    (ROOT / "data/samples/m1-import-results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    failures = [record["filename"] for record in records if record["status"] != "ready"]
    if failures:
        raise SystemExit(f"Import did not finish for: {', '.join(failures)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
