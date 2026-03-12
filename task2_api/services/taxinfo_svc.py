from task2_api.models import ChangeType, TaxInfo

from .changelog_svc import create_changelog
from .orphans_svc import cleanup_orphaned_tax_info


def sync_taxinfo(parent, new_input: list[dict] | None):
    if new_input is None:
        return
    existing_items = {obj.pid: obj for obj in parent.taxinfo.all()}
    wanted_pids = [item.get("pid") for item in new_input if item.get("pid")]
    obsolete_items = [
        obj for obj in existing_items.values() if obj.pid not in wanted_pids
    ]

    # remove obsolete items
    for obj in obsolete_items:
        parent.taxinfo.remove(obj)
        cleanup_orphaned_tax_info(obj.pid)

    # update existing or create new items
    for data in new_input:
        pid = data.get("pid", None)
        if pid:
            if pid in existing_items:
                # update existing item associated with current parent
                obj = existing_items[pid]
            else:
                # update item not associated with current parent
                obj = TaxInfo.objects.get(pid=pid)
            old_data = {"tin": obj.tin, "country": obj.country}
            obj.tin = data["tin"]
            obj.country = data["country"]
            obj.save()
            parent.taxinfo.add(obj)
            create_changelog(
                ChangeType.UPDATED, obj, old_data=old_data, new_data=obj.to_dict()
            )
        else:
            obj = TaxInfo.objects.create(**data)
            parent.taxinfo.add(obj)
            create_changelog(ChangeType.ADDED, obj, new_data=obj.to_dict())
