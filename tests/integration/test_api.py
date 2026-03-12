import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from task2_api.models import (
    ChangeLog,
    Company,
    Director,
    IdentityFile,
    Shareholder,
    TaxInfo,
)
from task2_api.serializers import (
    CompanySerializer,
)
from tests.factories import (
    CompanyFactory,
    DirectorFactory,
    IdentityFileFactory,
    ShareholderFactory,
    TaxInfoFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestCompanyPatch:

    def test_update_company_name_creates_changelog(self, api_client):
        company = CompanyFactory(name="Old Name")
        url = reverse("company-detail", kwargs={"pid": company.pid})

        payload = {"name": "New Name"}
        response = api_client.patch(url, payload, format="json")

        assert response.status_code == 200
        assert Company.objects.get(pid=company.pid).name == "New Name"

        log = ChangeLog.objects.filter(object_pid=company.pid).first()
        assert log.change_type == "updated"
        assert log.changes["old"]["name"] == "Old Name"
        assert log.changes["new"]["name"] == "New Name"

    def test_removes_orphaned_identity_files(self, api_client):
        shared_identity_file = IdentityFileFactory(pid="8888777766665555")
        shared_identityfile_pid = shared_identity_file.pid
        company = CompanyFactory()

        director = DirectorFactory(
            company=company,
            with_identity_files=[shared_identity_file],
            with_taxinfo=[],
        )
        director_pid = director.pid
        director_serialized = director.to_dict()
        shareholder = ShareholderFactory(
            company=company, with_identity_files=[shared_identity_file]
        )
        shareholder_pid = shareholder.pid
        shareholder_serialized = shareholder.to_dict()

        url = reverse("company-detail", kwargs={"pid": company.pid})

        response = api_client.patch(
            url,
            {
                "directors": [],
            },
            format="json",
        )
        assert response.status_code == 200

        assert Director.objects.count() == 0
        assert IdentityFile.objects.count() == 1

        assert (
            ChangeLog.objects.filter(
                object_type="IdentityFile", change_type="removed"
            ).count()
            == 0
        )

        api_client.patch(
            url,
            {
                "shareholders": [],
            },
            format="json",
        )

        assert Shareholder.objects.count() == 0
        # identity file removed as it's no longer used
        assert IdentityFile.objects.count() == 0

        logs = list(
            ChangeLog.objects.order_by("object_type", "change_type", "object_pid")
            .filter(object_type__in=["Director", "IdentityFile", "Shareholder"])
            .values_list("object_type", "change_type", "object_pid", "changes")
            .all()
        )
        assert logs == [
            (
                "Director",
                "removed",
                director_pid,
                {"old": director_serialized, "new": None},
            ),
            (
                "IdentityFile",
                "removed",
                shared_identityfile_pid,
                {"old": {"pid": shared_identityfile_pid}, "new": None},
            ),
            (
                "Shareholder",
                "removed",
                shareholder_pid,
                {"old": shareholder_serialized, "new": None},
            ),
        ]

    def test_removes_orphaned_tax_info_and_creates_changelogs(self, api_client):
        shared_tax_info = TaxInfoFactory()
        company = CompanyFactory(with_taxinfo=[shared_tax_info])
        director = DirectorFactory(company=company, with_taxinfo=[shared_tax_info])

        tax_info_pid = shared_tax_info.pid
        tax_info_serialized = shared_tax_info.to_dict()
        director_pid = director.pid
        director_serialized = director.to_dict()

        url = reverse("company-detail", kwargs={"pid": company.pid})

        api_client.patch(url, {"taxinfo": []}, format="json")

        assert TaxInfo.objects.count() == 1
        assert (
            ChangeLog.objects.filter(
                object_type="TaxInfo", change_type="removed"
            ).count()
            == 0
        )

        api_client.patch(url, {"directors": []}, format="json")

        assert Director.objects.count() == 0
        assert TaxInfo.objects.count() == 0

        logs = list(
            ChangeLog.objects.order_by("object_type", "change_type", "object_pid")
            .filter(object_type__in=["Director", "TaxInfo"])
            .values_list("object_type", "change_type", "object_pid", "changes")
        )
        assert logs == [
            (
                "Director",
                "removed",
                director_pid,
                {"old": director_serialized, "new": None},
            ),
            (
                "TaxInfo",
                "removed",
                tax_info_pid,
                {"old": tax_info_serialized, "new": None},
            ),
        ]

    def test_values_updated_and_changelogs_created(self, api_client):
        company = CompanyFactory(
            name="Old company name", with_taxinfo=[TaxInfoFactory(), TaxInfoFactory()]
        )
        old_director = DirectorFactory(
            company=company,
            with_identity_files=[
                IdentityFileFactory(),
                IdentityFileFactory(),
                IdentityFileFactory(),
            ],
            with_taxinfo=[TaxInfoFactory(), TaxInfoFactory(), TaxInfoFactory()],
        )
        serialized_old_company = company.to_dict()

        expected_identity_files_logs = [
            (
                "IdentityFile",
                "removed",
                id_file.pid,
                {"old": id_file.to_dict(), "new": None},
            )
            for id_file in old_director.identity_files.order_by("pid").all()
        ]
        expected_taxinfo_removal_logs = [
            (
                "TaxInfo",
                "removed",
                taxinfo.pid,
                {"old": taxinfo.to_dict(), "new": None},
            )
            for taxinfo in sorted(
                [*old_director.taxinfo.all(), *company.taxinfo.all()],
                key=lambda x: x.pid,
            )
        ]
        serialized_old_director = old_director.to_dict()

        url = reverse("company-detail", kwargs={"pid": company.pid})
        payload = {
            "name": "New company name",
            "taxinfo": [{"tin": "123654", "country": "PL"}],
            "directors": [{"full_name": "New Person"}],
        }
        api_client.patch(url, payload, format="json")

        company.refresh_from_db()
        assert company.name == payload["name"]
        assert company.taxinfo and list(
            company.taxinfo.values_list("tin", flat=True)
        ) == [payload["taxinfo"][0]["tin"]]
        assert company.taxinfo and list(
            company.taxinfo.values_list("country", flat=True)
        ) == [payload["taxinfo"][0]["country"]]

        new_director = company.directors.first()

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
                {"old": serialized_old_company, "new": company.to_dict()},
            ),
            (
                "Director",
                "added",
                new_director.pid,
                {
                    "old": None,
                    "new": {
                        **payload["directors"][0],
                        "pid": new_director.pid,
                        "taxinfo": [],
                        "identity_files": [],
                    },
                },
            ),
            (
                "Director",
                "removed",
                old_director.pid,
                {"old": serialized_old_director, "new": None},
            ),
            *expected_identity_files_logs,
            (
                "TaxInfo",
                "added",
                company.taxinfo.first().pid,
                {
                    "new": {
                        "country": "PL",
                        "pid": company.taxinfo.first().pid,
                        "tin": "123654",
                    },
                    "old": None,
                },
            ),
            *expected_taxinfo_removal_logs,
        ]
