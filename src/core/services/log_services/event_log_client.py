from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import clickhouse_connect
import structlog
from clickhouse_connect.driver.exceptions import DatabaseError
from django.conf import settings

from core.models import EventsLogOutBox

logger = structlog.get_logger(__name__)

EVENT_LOG_COLUMNS = [
    "event_type",
    "event_date_time",
    "environment",
    "event_context",
]


class EventLogClient:
    def __init__(self, client: clickhouse_connect.driver.Client) -> None:
        self._client = client

    @classmethod
    @contextmanager
    def init(cls) -> Generator["EventLogClient"]:
        client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            query_retries=2,
            connect_timeout=30,
            send_receive_timeout=10,
        )
        try:
            yield cls(client)
        except Exception as e:
            logger.error("error while executing clickhouse query", error=str(e))
        finally:
            client.close()

    def insert(
        self,
        data: list[EventsLogOutBox],
    ) -> bool:
        try:
            self._client.insert(
                data=self._convert_data(data),
                column_names=EVENT_LOG_COLUMNS,
                database=settings.CLICKHOUSE_SCHEMA,
                table=settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME,
            )
            return True
        except DatabaseError as e:
            logger.error("unable to insert data to clickhouse", error=str(e))
            return False

    def query(self, query: str) -> Any:  # noqa: ANN401
        logger.debug("executing clickhouse query", query=query)

        try:
            return self._client.query(query).result_rows
        except DatabaseError as e:
            logger.error("failed to execute clickhouse query", error=str(e))
            return

    def _convert_data(self, data: list[EventsLogOutBox]) -> list[tuple[Any]]:
        return [
            (
                outbox_event.event_type,
                outbox_event.event_date_time,
                outbox_event.environment,
                outbox_event.event_context,
            )
            for outbox_event in data
        ]
