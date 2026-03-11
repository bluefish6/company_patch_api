import re

import pytest
from django.db import IntegrityError

from task2_api.models import Company, generate_pid


def test_pid_is_numeric_and_has_16_chars():
    pid = generate_pid()
    assert re.match(r"^\d{16}$", pid)


@pytest.fixture()
def mocked_save(mocker):
    return mocker.patch("task2_api.models.super", create=True)().save


@pytest.mark.django_db
def test_pid_collision_retries(mocked_save):
    mocked_save.side_effect = [IntegrityError, IntegrityError, None]
    company = Company(name="Retry Test", date_of_incorporation="2026-01-01")

    company.save()
    assert mocked_save.call_count == 3


@pytest.mark.django_db
def test_pid_collision_gives_up_after_too_many_retries(mocked_save):
    mocked_save.side_effect = [IntegrityError] * 3
    company = Company(name="Retry Test", date_of_incorporation="2026-01-01")

    with pytest.raises(IntegrityError):
        company.save()
    assert mocked_save.call_count == 3
