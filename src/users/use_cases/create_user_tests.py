import pytest

from core.models import EventsLogOutBox
from users.use_cases import CreateUser, CreateUserRequest

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def f_use_case() -> CreateUser:
    return CreateUser()


def test_user_created(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email="test@email.com",
        first_name="Test",
        last_name="Testovich",
    )

    response = f_use_case.execute(request)

    assert response.result.email == "test@email.com"
    assert response.error == ""


def test_emails_are_unique(f_use_case: CreateUser) -> None:
    request = CreateUserRequest(
        email="test@email.com",
        first_name="Test",
        last_name="Testovich",
    )
    f_use_case.execute(request)
    assert EventsLogOutBox.objects.count() == 1
    response = f_use_case.execute(request)

    assert response.result is None
    assert response.error == "User with this email already exists"
    assert EventsLogOutBox.objects.filter(event_type="user_created").count() == 1
