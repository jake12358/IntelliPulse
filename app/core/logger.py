import logging
import sys
from contextlib import contextmanager
from time import perf_counter


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


@contextmanager
def log_timing(logger: logging.Logger, label: str):
    start = perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info("%s finished in %.1fms", label, elapsed_ms)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
