import traceback
from datetime import datetime, timedelta

import structlog
from django.conf import settings

from core.core_enums import EvenLogStatus
from core.models import EventsLogOutBox
from core.services.log_services.event_log_client import EventLogClient

logger = structlog.get_logger(__name__)


def set_sending_status_to_log_event_obj(log_event: EventsLogOutBox) -> EventsLogOutBox:
    log_event.send_status = EvenLogStatus.SENDING
    return log_event


def set_delivered_status_to_log_event_obj(log_event: EventsLogOutBox) -> EventsLogOutBox:
    log_event.send_status = EvenLogStatus.DELIVERED
    return log_event


def set_awaiting_deliver_status_to_log_event_obj(log_event: EventsLogOutBox) -> EventsLogOutBox:
    log_event.send_status = EvenLogStatus.AWAITING_DELIVER
    return log_event


def delete_delivered_events() -> None:
    try:
        logger.info("Deleting delivered events from outbox")
        deleted_rows: int = EventsLogOutBox.objects.filter(send_status=EvenLogStatus.DELIVERED).delete()
        logger.info(f"{deleted_rows} delivered events has been deleted from outbox")
    except Exception as e:
        logger.error(f"Deleting delivered events failed: \n{e}:{traceback.format_exc()}")


class EventLogService:
    event_switch_status_mapper = {
        EvenLogStatus.AWAITING_DELIVER: set_awaiting_deliver_status_to_log_event_obj,
        EvenLogStatus.DELIVERED: set_delivered_status_to_log_event_obj,
        EvenLogStatus.SENDING: set_sending_status_to_log_event_obj,
    }

    def __init__(
        self,
        ttl_minutes: int = None,
        retries_number: int = settings.FAILED_LOG_SENDING_RETRIES,
    ) -> None:
        self.event_partition_collector: list[EventsLogOutBox] = []
        self.service_expiration_time: datetime | None = None
        self.retries_number_left: int = retries_number
        self.success_partitions_send_counter = 0
        self.failed_partitions_send_counter = 0
        self._calculate_service_expiration_time(ttl_minutes=ttl_minutes)

    def _calculate_service_expiration_time(self, ttl_minutes: int) -> datetime:
        """
        Calculate the service expiration time based on the current time and TTL in minutes.
        The purpose of this parameter is to shut down service instance if it constantly fails.
        Also, it allows collect metrics and customize configurations.
        """
        if ttl_minutes:
            return datetime.now(tz=settings.TIME_ZONE) + timedelta(minutes=ttl_minutes)

    def process_log_events(self) -> None:
        try:
            if not self._can_send_events():
                self._log_service_report()
                return
            self._get_next_events_partition()
            self._update_partition_status(new_status=EvenLogStatus.SENDING)
            is_sent: bool = self._send_log_events()
            if is_sent:
                self._update_partition_status(new_status=EvenLogStatus.DELIVERED)
                self._clean_event_partition_collector()
                self.success_partitions_send_counter += 1
                self.process_log_events()
            else:
                self._update_partition_status(new_status=EvenLogStatus.AWAITING_DELIVER)
                self.failed_partitions_send_counter += 1
                self.retries_number_left -= 1
                self.process_log_events()
        except Exception as e:
            logger.error(f"Failed to send log events {e}: \n{traceback.format_exc()}")
            self._update_partition_status(new_status=EvenLogStatus.AWAITING_DELIVER)
            self.failed_partitions_send_counter += 1
            self.retries_number_left -= 1
            self.process_log_events()

    def _can_send_events(self) -> bool:
        if not self._is_next_event_partition_available():
            logger.info(f"Minimum batch for send is {settings.LOG_EVENTS_PARTITION_QUANTITY})")
            return False
        if self._is_service_ttl_expired():
            logger.info("Service TTL has been expired. Service shutting down")
            return False
        if not self.retries_number_left:
            return False
        return True

    def _is_next_event_partition_available(self) -> bool:
        partition_quantity = self._get_log_event_partition_quantity()
        unpublished_events_quantity = self._get_unpublished_events_quantity()
        if unpublished_events_quantity >= partition_quantity:
            return True
        else:
            return False

    def _is_service_ttl_expired(self) -> bool:
        if self.service_expiration_time is None:
            return False  # If no expiration time is set, consider it not expired
        return datetime.now(tz=settings.TIME_ZONE) > self.service_expiration_time

    def _get_log_event_partition_quantity(self) -> int:
        return settings.LOG_EVENTS_PARTITION_QUANTITY

    def _get_unpublished_events_quantity(self) -> int:
        return EventsLogOutBox.objects.filter(
            send_status=EvenLogStatus.AWAITING_DELIVER,
        ).count()

    def _get_next_events_partition(self) -> None:
        # NOTE: if retry run no need query data again
        if self.event_partition_collector:
            return
        partition_size = self._get_log_event_partition_quantity()
        self.event_partition_collector = list(
            EventsLogOutBox.objects.filter(
                send_status=EvenLogStatus.AWAITING_DELIVER,
            ).order_by("created_at")[:partition_size],
        )

    def _update_partition_status(self, new_status: EvenLogStatus) -> None:
        list(
            map(
                self.event_switch_status_mapper.get(new_status),
                self.event_partition_collector,
            ),
        )
        EventsLogOutBox.objects.bulk_update(
            self.event_partition_collector,
            ["send_status"],
        )

    def _send_log_events(self) -> bool:
        with EventLogClient.init() as client:
            is_inserted: bool = client.insert(
                data=self.event_partition_collector,
            )
            return is_inserted

    def _clean_event_partition_collector(self) -> None:
        self.event_partition_collector = []

    def _log_service_report(self) -> None:
        logger.info(
            f"Success events partitions sent quantity: {self.success_partitions_send_counter}\n"
            f"Failed events partitions sent quantity: {self.failed_partitions_send_counter}",
        )
