import importlib
import os
import subprocess
import sys


def check_module(name: str) -> bool:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", "unknown")
        print(f"[OK] {name}: {version}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {exc.__class__.__name__}: {exc}")
        return False


def main() -> int:
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"VIRTUAL_ENV: {os.getenv('VIRTUAL_ENV', '<not set>')}")
    print()

    checks = [
        check_module("redis"),
        check_module("kombu"),
        check_module("kombu.transport.redis"),
        check_module("celery"),
        check_module("fastapi"),
    ]

    print()
    for package in ("redis", "kombu", "celery"):
        try:
            output = subprocess.check_output(
                [sys.executable, "-m", "pip", "show", package],
                text=True,
                stderr=subprocess.STDOUT,
            )
            interesting = [
                line
                for line in output.splitlines()
                if line.startswith(("Name:", "Version:", "Location:"))
            ]
            print("\n".join(interesting))
        except Exception as exc:
            print(f"pip show {package}: {exc}")

    try:
        transport = importlib.import_module("kombu.transport.redis")
        redis_obj = getattr(transport, "redis", "<missing>")
        print(f"kombu.transport.redis.redis: {redis_obj!r}")
        print(f"kombu transport file: {getattr(transport, '__file__', '<unknown>')}")
    except Exception as exc:
        print(f"kombu redis transport detail: {exc.__class__.__name__}: {exc}")

    if not all(checks):
        print("\nFix suggestion:")
        print('python -m pip install --upgrade "celery[redis]>=5.3,<6" "redis>=5,<6" "kombu>=5.3,<6"')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
