import pytest

from task2_api.models import ChangeLog, ChangeType
from task2_api.services.changelog_svc import create_changelog
from tests.factories import CompanyFactory, DirectorFactory


@pytest.mark.django_db
class TestCreateChangelog:

    @pytest.mark.parametrize(
        [
            "change_type",
            "pid_from_old_data",
            "old_data",
            "new_data",
            "expected_log_created",
        ],
        [
            pytest.param(
                ChangeType.UPDATED,
                False,
                {"full_name": "Old Name"},
                {"full_name": "New Name"},
                True,
                id="updated",
            ),
            pytest.param(
                ChangeType.UPDATED,
                False,
                {"full_name": "Same Name"},
                {"full_name": "Same Name"},
                False,
                id="updated without changes",
            ),
            pytest.param(
                ChangeType.REMOVED,
                True,
                {"pid": "1234567812345678", "full_name": "Deleted Director"},
                None,
                True,
                id="deleted",
            ),
            pytest.param(
                ChangeType.ADDED,
                False,
                None,
                {"full_name": "New Director"},
                True,
                id="added",
            ),
        ],
    )
    def test_creates_changelog_with_expected_values(
        self,
        change_type,
        pid_from_old_data,
        old_data,
        new_data,
        expected_log_created,
    ):
        company = CompanyFactory()
        director = DirectorFactory(company=company)

        original_pid = director.pid

        if pid_from_old_data:
            director.pid = None
            expected_pid = old_data.get("pid")
        else:
            expected_pid = original_pid

        # Execution
        create_changelog(change_type, director, old_data=old_data, new_data=new_data)

        # Verification
        assert ChangeLog.objects.count() == (1 if expected_log_created else 0)

        if expected_log_created:
            log = ChangeLog.objects.first()
            assert log.change_type == change_type
            assert log.object_type == "Director"
            assert log.object_pid == expected_pid
            assert log.changes == {"old": old_data, "new": new_data}
