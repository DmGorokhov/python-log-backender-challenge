from typing import Any, Protocol

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.base_model import Model
from core.models import EventsLogOutBox
from core.utils import to_snake_case


class UseCaseRequest(Model):
    pass


class UseCaseResponse(Model):
    result: Any = None
    error: str = ""


class UseCase(Protocol):
    @transaction.atomic()
    def execute(self, request: UseCaseRequest) -> UseCaseResponse:
        with structlog.contextvars.bound_contextvars(
            **self._get_context_vars(request),
        ):
            response = self._execute(request)
            event = self._get_log_event(response)
            if event:
                self._log_event(event)
            return response

    def _get_context_vars(self, request: UseCaseRequest) -> dict[str, Any]:  # noqa: ARG002
        """
        !!! WARNING:
            This method is calling out of transaction so do not make db
            queries in this method.
        """
        return {
            "use_case": self.__class__.__name__,
        }

    def _log_event(self, log_event: Model) -> None:
        event_type = to_snake_case(log_event.__class__.__name__)
        new_event = EventsLogOutBox.objects.create(
            event_type=event_type,
            event_date_time=timezone.now(),
            environment=settings.ENVIRONMENT,
            event_context=log_event.model_dump_json(),
        )
        return new_event

    def _get_log_event(self, response: UseCaseResponse) -> Model | None: # noqa ARG002
        """
        Implement this method, if you need write event
        """
        return

    def _execute(self, request: UseCaseRequest) -> UseCaseResponse:
        raise NotImplementedError()
