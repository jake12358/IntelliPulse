import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.tasks.worker_tasks import process_document


SAMPLES = [
    ("飞书", ROOT / "samples" / "feishu.txt"),
    ("钉钉", ROOT / "samples" / "dingtalk.txt"),
    ("企业微信", ROOT / "samples" / "wecom.txt"),
]


def main() -> None:
    total = 0
    for company, path in SAMPLES:
        result = process_document(str(path), company)
        inserted = int(result["inserted"])
        total += inserted
        print(f"{company}: inserted {inserted} chunks from {path.name}")
    print(f"Done. Total chunks: {total}")


if __name__ == "__main__":
    main()
