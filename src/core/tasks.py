from core.celery_app import app
from core.services.log_services.even_log_service import EventLogService, delete_delivered_events


@app.task
def process_events() -> None:
    event_log_service = EventLogService()
    event_log_service.process_log_events()


@app.task
def clean_events_outbox() -> None:
    delete_delivered_events()
