from collections import defaultdict

from ..models import ChangeType, Director
from .changelog_svc import create_changelog
from .identity_files_svc import sync_identity_files
from .orphans_svc import (
    cleanup_potential_orphans,
    extend_potential_orphans,
)
from .taxinfo_svc import sync_taxinfo


def sync_collections(director, taxinfo, identity_files):
    sync_taxinfo(director, taxinfo)
    sync_identity_files(director, identity_files)


def sync_directors(company, new_directors: list[dict] | None):
    if new_directors is None:
        return
    new_input = new_directors

    existing_items = {obj.pid: obj for obj in company.directors.all()}
    wanted_pids = [item.get("pid") for item in new_input if item.get("pid")]
    obsolete_items = [
        obj for obj in existing_items.values() if obj.pid not in wanted_pids
    ]
    potential_orphans: defaultdict[str, set] = defaultdict(set)

    # remove obsolete items
    for obj in obsolete_items:
        potential_orphans = extend_potential_orphans(potential_orphans, obj)
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
                obj = Director.objects.get(pid=pid)

            potential_orphans = extend_potential_orphans(potential_orphans, obj)
            old_data = obj.to_dict()
            obj.full_name = data["full_name"]
            company.directors.add(obj)
            obj.save()
            sync_collections(
                director=obj,
                taxinfo=data.get("taxinfo", []),
                identity_files=data.get("identity_files", []),
            )
            create_changelog(
                ChangeType.UPDATED, obj, old_data=old_data, new_data=obj.to_dict()
            )
        else:
            obj = Director.objects.create(company=company, full_name=data["full_name"])
            company.directors.add(obj)
            obj.save()
            sync_collections(
                director=obj,
                taxinfo=data.get("taxinfo", []),
                identity_files=data.get("identity_files", []),
            )
            create_changelog(ChangeType.ADDED, obj, new_data=obj.to_dict())

    cleanup_potential_orphans(potential_orphans)
