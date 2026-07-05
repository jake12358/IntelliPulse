from app.core.config import get_settings

settings = get_settings()

try:
    from celery import Celery

    celery_app = Celery(
        "intellipulse",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.tasks.worker_tasks"],
    )
    celery_app.conf.update(task_track_started=True, timezone="Asia/Shanghai")
except Exception:

    class _LocalTask:
        def __init__(self, fn):
            self.fn = fn
            self.__name__ = fn.__name__

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

        def delay(self, *args, **kwargs):
            class Result:
                id = "local-task"

            self.fn(*args, **kwargs)
            return Result()

    class _LocalCelery:
        def task(self, *args, **kwargs):
            def decorator(fn):
                return _LocalTask(fn)

            return decorator

    celery_app = _LocalCelery()
