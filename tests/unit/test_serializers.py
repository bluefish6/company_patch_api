import pytest

from task2_api.models import (
    ChangeLog,
    Director,
    IdentityFile,
    Shareholder,
    TaxInfo,
)
from task2_api.serializers import (
    CompanySerializer,
    DirectorSerializer,
    IdentityFileSerializer,
    ShareholderSerializer,
    TaxInfoSerializer,
)
from tests.factories import CompanyFactory, DirectorFactory, IdentityFileFactory

pids = [
    "1234567890123456",
    "2345678901234567",
    "3456789012345678",
    "4567890123456789",
    "5678901234567890",
    "6789012345678901",
]


@pytest.mark.django_db
class TestCompanyPatch:

    def test_full_nested_update_and_changelog(self):
        company = CompanyFactory(name="Old", with_taxinfo=[])
        identity_file1 = IdentityFileFactory(pid=pids[0])
        director1 = DirectorFactory(
            company=company,
            full_name="Director 1",
            with_identity_files=[identity_file1],
            with_taxinfo=[],
        )
        director1_before_changes_serialized = DirectorSerializer(director1).data
        old_company_serialized = CompanySerializer(company).data

        payload = {
            "name": "New Name",
            "directors": [
                {
                    "pid": director1.pid,
                    "full_name": "Director 1 Updated",
                    "identity_files": [{"pid": pids[1]}],
                    "taxinfo": [{"tin": "123456789", "country": "US"}],
                },
                {
                    "full_name": "New Director",
                    "identity_files": [{"pid": pids[2]}],
                    "taxinfo": [{"tin": "234567890", "country": "US"}],
                },
            ],
            "shareholders": [
                {
                    "full_name": "Shareholder 1",
                    "percentage": 25,
                    "identity_files": [{"pid": pids[3]}],
                },
            ],
        }

        serializer = CompanySerializer(company, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        company.refresh_from_db()
        director1.refresh_from_db()
        assert company.name == "New Name"
        assert company.directors.count() == 2
        assert company.shareholders.count() == 1

        assert not IdentityFile.objects.filter(pid=pids[0]).exists()
        assert IdentityFile.objects.filter(pid=pids[1]).exists()
        assert IdentityFile.objects.filter(pid=pids[2]).exists()

        new_directors = Director.objects.exclude(pid=director1.pid).all()
        assert len(new_directors) == 1
        new_director = new_directors[0]
        new_shareholders = Shareholder.objects.all()
        assert len(new_shareholders) == 1
        new_shareholder = new_shareholders[0]
        new_id_files = (
            IdentityFile.objects.exclude(pid=identity_file1.pid).order_by("pid").all()
        )
        assert len(new_id_files) == 3
        new_taxinfos = TaxInfo.objects.order_by("pid").all()
        assert len(new_taxinfos) == 2
        logs = list(
            ChangeLog.objects.order_by("object_type", "change_type", "object_pid")
            .values_list("object_type", "change_type", "object_pid", "changes")
            .all()
        )
        assert logs == [
            (
                "Company",
                "updated",
                company.pid,
                {"old": old_company_serialized, "new": CompanySerializer(company).data},
            ),
            (
                "Director",
                "added",
                new_director.pid,
                {"old": None, "new": DirectorSerializer(new_director).data},
            ),
            (
                "Director",
                "updated",
                director1.pid,
                {
                    "old": director1_before_changes_serialized,
                    "new": DirectorSerializer(director1).data,
                },
            ),
            (
                "IdentityFile",
                "added",
                new_id_files[0].pid,
                {"old": None, "new": IdentityFileSerializer(new_id_files[0]).data},
            ),
            (
                "IdentityFile",
                "added",
                new_id_files[1].pid,
                {"old": None, "new": IdentityFileSerializer(new_id_files[1]).data},
            ),
            (
                "IdentityFile",
                "added",
                new_id_files[2].pid,
                {"old": None, "new": IdentityFileSerializer(new_id_files[2]).data},
            ),
            (
                "IdentityFile",
                "removed",
                identity_file1.pid,
                {"old": None, "new": None},
            ),
            (
                "Shareholder",
                "added",
                new_shareholder.pid,
                {"old": None, "new": ShareholderSerializer(new_shareholder).data},
            ),
            (
                "TaxInfo",
                "added",
                new_taxinfos[0].pid,
                {"old": None, "new": TaxInfoSerializer(new_taxinfos[0]).data},
            ),
            (
                "TaxInfo",
                "added",
                new_taxinfos[1].pid,
                {"old": None, "new": TaxInfoSerializer(new_taxinfos[1]).data},
            ),
        ]

        logs = ChangeLog.objects.all()
        assert all(l.timestamp for l in logs)

    def test_no_change_no_log(self):
        company = CompanyFactory(
            name="Unchanged name", date_of_incorporation="2020-01-01", with_taxinfo=[]
        )
        ChangeLog.objects.all().delete()

        serializer = CompanySerializer(
            company, data={"name": "Unchanged name"}, partial=True
        )
        serializer.is_valid()
        serializer.save()

        assert (
            ChangeLog.objects.filter(
                change_type="updated", object_type="Company"
            ).count()
            == 0
        )
