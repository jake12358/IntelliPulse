import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.redis_client import redis_vector_client
from app.db.repository import postgres_status


async def main() -> int:
    chunks = redis_vector_client._load_chunks_from_redis()
    print(f"Redis available: {redis_vector_client._redis is not None}")
    print(f"Redis chunks: {len(chunks)}")
    status = await postgres_status()
    print(f"Postgres available: {status['available']}")
    print(f"Postgres documents: {status['documents']}")
    print(f"Postgres chunks: {status['chunks']}")
    if status["error"]:
        print(f"Postgres error: {status['error']}")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
