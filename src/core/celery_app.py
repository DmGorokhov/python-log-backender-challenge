import os

from celery import Celery
from django.conf import settings

os.environ.setdefault(key="DJANGO_SETTINGS_MODULE", value="core.settings")

app = Celery(broker=settings.CELERY_BROKER, include=["src.core.tasks"])

app.conf.task_default_queue = "normal"
app.conf.task_track_started = True
app.conf.result_extended = True
app.config_from_object(obj="django.conf:settings", namespace="CELERY")
app.conf.timezone = "Europe/Moscow"
app.conf.broker_connection_retry_on_startup = True
app.worker_cancel_long_running_tasks_on_connection_loss = True
app.autodiscover_tasks(packages=lambda: settings.INSTALLED_APPS)
