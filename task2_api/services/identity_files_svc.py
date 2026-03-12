from task2_api.models import ChangeType, IdentityFile

from .changelog_svc import create_changelog
from .orphans_svc import cleanup_orphaned_identity_file


def sync_identity_files(parent, new_input):
    if new_input is None:
        return

    existing_items = {obj.pid: obj for obj in parent.identity_files.all()}
    wanted_pids = [item.get("pid") for item in new_input if item.get("pid")]
    obsolete_items = [
        obj for obj in existing_items.values() if obj.pid not in wanted_pids
    ]

    # remove obsolete items
    for obj in obsolete_items:
        parent.identity_files.remove(obj)
        cleanup_orphaned_identity_file(obj.pid)

    # update existing or create new items
    for data in new_input:
        pid = data.get("pid", None)
        if pid:
            if pid in existing_items:
                continue
            # item not associated with current parent
            obj, created = IdentityFile.objects.get_or_create(pid=pid)
            parent.identity_files.add(obj)
            if created:
                create_changelog(ChangeType.ADDED, obj, new_data=obj.to_dict())
