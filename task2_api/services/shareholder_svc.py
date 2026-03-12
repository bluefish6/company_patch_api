from collections import defaultdict

from ..models import ChangeType, Shareholder
from .changelog_svc import create_changelog
from .identity_files_svc import sync_identity_files
from .orphans_svc import (
    cleanup_potential_orphans,
    extend_potential_orphans,
)


def sync_collections(shareholder, identity_files):
    sync_identity_files(shareholder, identity_files)


def sync_shareholders(company, new_shareholders: list[dict] | None):
    if new_shareholders is None:
        return
    new_input = new_shareholders

    existing_items = {obj.pid: obj for obj in company.shareholders.all()}
    wanted_pids = [item.get("pid") for item in new_input if item.get("pid")]
    obsolete_items = [
        obj for obj in existing_items.values() if obj.pid not in wanted_pids
    ]
    potential_orphans: defaultdict[str, set] = defaultdict(set)

    # remove obsolete items
    for obj in obsolete_items:
        potential_orphans = extend_potential_orphans(
            potential_orphans,
            obj,
        )
        create_changelog(ChangeType.REMOVED, obj, old_data=obj.to_dict())
        obj.delete()

    # update existing or create new items
    for data in new_input:
        pid = data.get("pid", None)
        if pid:
            if pid in existing_items:
                # update existing item associated with current parent
                obj = existing_items[pid]
            else:
                # update item not associated with current parent
                obj = Shareholder.objects.get(pid=pid)
                potential_orphans = extend_potential_orphans(potential_orphans, obj)
            old_data = obj.to_dict()
            obj.full_name = data["full_name"]
            obj.percentage = data["percentage"]
            company.shareholders.add(obj)
            obj.save()
            sync_collections(
                shareholder=obj, identity_files=data.get("identity_files", [])
            )
            create_changelog(
                ChangeType.UPDATED, obj, old_data=old_data, new_data=obj.to_dict()
            )
        else:
            obj = Shareholder.objects.create(
                company=company,
                full_name=data["full_name"],
                percentage=data["percentage"],
            )
            company.shareholders.add(obj)
            obj.save()
            sync_collections(
                shareholder=obj, identity_files=data.get("identity_files", [])
            )
            create_changelog(ChangeType.ADDED, obj, new_data=obj.to_dict())

    cleanup_potential_orphans(potential_orphans)
