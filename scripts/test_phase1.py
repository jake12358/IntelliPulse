import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.redis_client import redis_vector_client
from app.tasks.worker_tasks import process_document


def main() -> None:
    settings = get_settings()
    sample = settings.upload_path / "sample-phase1.txt"
    sample.write_text(
        "飞书提供即时沟通、文档协作和项目管理能力。价格按版本区分，适合成长型企业。\n"
        "钉钉强调组织管理、审批流和考勤能力，在中国企业市场覆盖广泛。\n",
        encoding="utf-8",
    )
    result = process_document(str(sample), "飞书")
    vector = result["chunks"][0]["embedding"]
    found = redis_vector_client.vector_search(vector, top_k=3)
    assert found, "No vector data found after insertion"
    print({"inserted": result["inserted"], "found": len(found), "top": found[0]["content"][:60]})


if __name__ == "__main__":
    main()
