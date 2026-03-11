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
    DirectorSerializer,
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
        shareholder = ShareholderFactory(
            company=company, with_identity_files=[shared_identity_file]
        )
        shareholder_pid = shareholder.pid

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
                {"old": None, "new": None},
            ),
            (
                "IdentityFile",
                "removed",
                shared_identityfile_pid,
                {"old": None, "new": None},
            ),
            (
                "Shareholder",
                "removed",
                shareholder_pid,
                {"old": None, "new": None},
            ),
        ]

    def test_removes_orphaned_tax_info_and_creates_changelogs(self, api_client):
        shared_tax_info = TaxInfoFactory()
        company = CompanyFactory(with_taxinfo=[shared_tax_info])
        director = DirectorFactory(company=company, with_taxinfo=[shared_tax_info])

        tax_info_pid = shared_tax_info.pid
        director_pid = director.pid
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
                {"old": None, "new": None},
            ),
            (
                "TaxInfo",
                "removed",
                tax_info_pid,
                {"old": None, "new": None},
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
        serialized_old_company = dict(CompanySerializer(company).data)

        expected_identity_files_logs = [
            (
                "IdentityFile",
                "removed",
                id_file.pid,
                {"old": None, "new": None},
            )
            for id_file in old_director.identity_files.order_by("pid").all()
        ]
        expected_director_taxinfo_removal_logs = [
            (
                "TaxInfo",
                "removed",
                taxinfo.pid,
                {"old": None, "new": None},
            )
            for taxinfo in old_director.taxinfo.order_by("pid").all()
        ]

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
                {"old": serialized_old_company, "new": CompanySerializer(company).data},
            ),
            (
                "Director",
                "added",
                new_director.pid,
                {"old": None, "new": dict(DirectorSerializer(new_director).data)},
            ),
            (
                "Director",
                "removed",
                old_director.pid,
                {"old": None, "new": None},
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
            *expected_director_taxinfo_removal_logs,
        ]
