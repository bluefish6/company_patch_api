from collections import defaultdict

from django.db import transaction

from task2_api.models import ChangeType, IdentityFile, TaxInfo
from task2_api.services.changelog_svc import create_changelog


def get_potential_orphan_pids(obj):
    potential_orphans = {
        "taxinfo": (
            list(obj.taxinfo.values_list("pid", flat=True))
            if hasattr(obj, "taxinfo")
            else []
        ),
        "identity_files": (
            list(obj.identity_files.values_list("pid", flat=True))
            if hasattr(obj, "identity_files")
            else []
        ),
    }
    return potential_orphans


def extend_potential_orphans(
    potential_orphans: defaultdict[str, set], obj
) -> defaultdict[str, set]:
    new_potential_orphans = get_potential_orphan_pids(obj)
    for k, v in new_potential_orphans.items():
        potential_orphans[k].update(v)
    return potential_orphans


def cleanup_potential_orphans(potential_orphan_pids):
    for pid in potential_orphan_pids["taxinfo"]:
        cleanup_orphaned_tax_info(pid)
    for pid in potential_orphan_pids["identity_files"]:
        cleanup_orphaned_identity_file(pid)


def cleanup_orphaned_identity_file(identity_file_pid: str):
    with transaction.atomic():
        identity_file_obj = (
            IdentityFile.objects.select_for_update()
            .filter(pid=identity_file_pid)
            .first()
        )
        if identity_file_obj and not (
            identity_file_obj.directors.exists()
            or identity_file_obj.shareholders.exists()
        ):
            create_changelog(
                ChangeType.REMOVED,
                identity_file_obj,
                old_data=identity_file_obj.to_dict(),
            )
            identity_file_obj.delete()


def cleanup_orphaned_tax_info(tax_info_pid: str):
    with transaction.atomic():
        tax_info_obj = (
            TaxInfo.objects.select_for_update().filter(pid=tax_info_pid).first()
        )
        if tax_info_obj and not (
            tax_info_obj.companies.exists() or tax_info_obj.directors.exists()
        ):
            create_changelog(
                ChangeType.REMOVED, tax_info_obj, old_data=tax_info_obj.to_dict()
            )
            tax_info_obj.delete()
