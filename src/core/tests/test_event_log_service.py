import pytest
from clickhouse_connect.driver import Client
from django.conf import settings
from model_bakery import baker

from core.core_enums import EvenLogStatus
from core.models import EventsLogOutBox
from core.services.log_services.even_log_service import EventLogService, delete_delivered_events

pytestmark = [pytest.mark.django_db]

log_events_partition_qty = settings.LOG_EVENTS_PARTITION_QUANTITY

log_events_use_cases = [
    # NOTE: partition_qty, expected_send_events, expected_left_events
    (log_events_partition_qty, log_events_partition_qty, 0),
    (log_events_partition_qty - 1, 0, log_events_partition_qty - 1),
    (log_events_partition_qty + 1, log_events_partition_qty, 1),
    (log_events_partition_qty * 3, log_events_partition_qty * 3, 0),
]


@pytest.mark.parametrize(
    "log_events_in_db, expected_send_events, expected_left_events",
    log_events_use_cases,
)
def test_publish_log_events(
    log_events_in_db: int,
    expected_send_events: int,
    expected_left_events: int,
    f_ch_client: Client,
) -> None:
    baker.make(
        EventsLogOutBox,
        _quantity=log_events_in_db,
    )
    log_event_service = EventLogService()
    log_event_service.process_log_events()

    assert EventsLogOutBox.objects.filter(send_status=EvenLogStatus.DELIVERED).count() == expected_send_events
    assert EventsLogOutBox.objects.filter(send_status=EvenLogStatus.AWAITING_DELIVER).count() == expected_left_events
    ch_inserted_rows = f_ch_client.query("SELECT COUNT(*) FROM default.event_log").result_rows[0][0]
    assert ch_inserted_rows == expected_send_events

    expected_partition_sent = log_events_in_db // log_events_partition_qty
    assert log_event_service.success_partitions_send_counter == expected_partition_sent
    assert log_event_service.failed_partitions_send_counter == 0


def false_send_stock_result() -> bool:
    return False


def test_publish_log_events_ch_client_error(
    f_ch_client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Emulate failed insert data in ch
    """
    baker.make(
        EventsLogOutBox,
        _quantity=log_events_partition_qty,
    )
    log_event_service = EventLogService()

    monkeypatch.setattr(
        log_event_service,
        "_send_log_events",
        false_send_stock_result,
    )

    log_event_service.process_log_events()

    assert EventsLogOutBox.objects.filter(send_status=EvenLogStatus.DELIVERED).count() == 0
    assert (
        EventsLogOutBox.objects.filter(send_status=EvenLogStatus.AWAITING_DELIVER).count() == log_events_partition_qty
    )
    ch_inserted_rows = f_ch_client.query("SELECT COUNT(*) FROM default.event_log").result_rows[0][0]
    assert ch_inserted_rows == 0
    assert log_event_service.failed_partitions_send_counter == settings.FAILED_LOG_SENDING_RETRIES


def test_delete_delivered_events() -> None:
    init_batch_size_by_send_status = 10
    baker.make(
        EventsLogOutBox,
        _quantity=init_batch_size_by_send_status,
        send_status=EvenLogStatus.DELIVERED,
    )
    baker.make(
        EventsLogOutBox,
        _quantity=init_batch_size_by_send_status,
        send_status=EvenLogStatus.AWAITING_DELIVER,
    )
    baker.make(
        EventsLogOutBox,
        _quantity=init_batch_size_by_send_status,
        send_status=EvenLogStatus.SENDING,
    )

    delete_delivered_events()

    assert EventsLogOutBox.objects.filter(send_status=EvenLogStatus.DELIVERED).count() == 0
    assert (
        EventsLogOutBox.objects.filter(send_status=EvenLogStatus.AWAITING_DELIVER).count()
        == init_batch_size_by_send_status
    )
    assert EventsLogOutBox.objects.filter(send_status=EvenLogStatus.SENDING).count() == init_batch_size_by_send_status
