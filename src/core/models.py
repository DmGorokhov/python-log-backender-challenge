
from django.db import models
from django.utils import timezone

from core.core_enums import EvenLogStatus


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using= None, # noqa
        update_fields=None,  # noqa
    ) -> None:
        # https://docs.djangoproject.com/en/5.1/ref/models/fields/#django.db.models.DateField.auto_now
        self.updated_at = timezone.now()

        if isinstance(update_fields, list):
            update_fields.append("updated_at")
        elif isinstance(update_fields, set):
            update_fields.add("updated_at")

        super().save(force_insert, force_update, using, update_fields)


class EventsLogOutBox(TimeStampedModel):
    event_type = models.CharField(max_length=255)
    event_date_time = models.DateTimeField()
    environment = models.CharField(max_length=255)
    event_context = models.TextField()
    send_status = models.CharField(
        choices=EvenLogStatus.choices(),
        max_length=50,
        help_text="Event delivery state",
        default=EvenLogStatus.AWAITING_DELIVER,
    )
