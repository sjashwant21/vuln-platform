from celery import Celery

# We can reuse the FastAPI configuration
from app.config import get_settings

cfg = get_settings()

celery_app = Celery(
    "vulnassess_worker",
    broker=cfg.celery_broker_url,
    backend=cfg.celery_result_backend,
    include=[
        "app.workers.tasks.scanner",
        "app.workers.tasks.analyst",
        "app.workers.tasks.trivy_scanner",
    ],
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 mins soft limit
)
