"""Download the four official source files, pinning revision and checking SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = "benchen4395/KuaiSearch"
FILES = ["recall_lite/train.jsonl", "users_lite/train.jsonl", "relevance/train.jsonl", "items_lite/train.jsonl"]


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "data/raw/kuaisearch")
    parser.add_argument("--revision", default="16f555af360f6a86209f60eb1f12462f9e25be2c")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    tree = get_json(f"https://huggingface.co/api/datasets/{REPO}/tree/{args.revision}?recursive=true&limit=1000")
    entries = {entry["path"]: entry for entry in tree}
    manifest = {"repository": REPO, "revision": args.revision, "files": []}
    for name in FILES:
        entry = entries[name]
        target = args.destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        expected_hash = entry["lfs"]["oid"]
        expected_size = entry["size"]
        url = f"https://huggingface.co/datasets/{REPO}/resolve/{args.revision}/{name}"
        record = {"path": name, "bytes": expected_size, "sha256": expected_hash, "url": url}
        manifest["files"].append(record)
        if target.exists() and target.stat().st_size == expected_size and sha256(target) == expected_hash:
            record["verified"] = True
            print(f"Verified existing {name}", flush=True)
            continue
        partial = target.with_suffix(target.suffix + ".part")
        for attempt in range(1, 33):
            start = partial.stat().st_size if partial.exists() else 0
            try:
                headers = {"User-Agent": "KuaiSearchOps/0.1"}
                if start:
                    headers["Range"] = f"bytes={start}-"
                request = urllib.request.Request(url + f"?download=true&attempt={attempt}", headers=headers)
                with urllib.request.urlopen(request, timeout=120) as response:
                    if start and response.status != 206:
                        start = 0
                    if start:
                        content_range = response.headers.get("Content-Range", "")
                        if not content_range.startswith(f"bytes {start}-"):
                            raise RuntimeError("Server returned an unexpected resume range")
                    with partial.open("ab" if start else "wb") as output:
                        downloaded = start
                        last_print = time.monotonic()
                        print(f"Downloading {name}: {downloaded:,}/{expected_size:,} bytes", flush=True)
                        while chunk := response.read(4 * 1024 * 1024):
                            output.write(chunk)
                            downloaded += len(chunk)
                            if time.monotonic() - last_print >= 10:
                                print(f"  {name}: {100 * downloaded / expected_size:.1f}% ({downloaded:,} bytes)", flush=True)
                                last_print = time.monotonic()
                if partial.stat().st_size != expected_size:
                    raise RuntimeError("File length differs from official metadata")
                actual_hash = sha256(partial)
                if actual_hash != expected_hash:
                    raise RuntimeError("SHA256 differs from official metadata; preserve the partial file for inspection")
                partial.replace(target)
                record["verified"] = True
                print(f"SHA256 verified: {name}", flush=True)
                break
            except Exception as error:
                print(f"Attempt {attempt} failed: {error}", flush=True)
                if attempt == 32:
                    raise
        (args.destination / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Download complete: {args.destination}", flush=True)


if __name__ == "__main__":
    main()
