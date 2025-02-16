from collections.abc import Generator

import clickhouse_connect
import pytest
from clickhouse_connect.driver import Client
from django.conf import settings


@pytest.fixture(scope="module")
def f_ch_client() -> Client:
    client = clickhouse_connect.get_client(host="clickhouse")
    yield client
    client.close()


@pytest.fixture(autouse=True)
def f_clean_up_event_log(f_ch_client: Client) -> Generator:
    f_ch_client.query(f"TRUNCATE TABLE {settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME}")
    yield
