from typing import cast

from task2_api.models import ChangeLog, ChangeType, PIDMixin


def create_changelog(
    change_type: ChangeType,
    obj: PIDMixin,
    old_data: dict | None = None,
    new_data: dict | None = None,
):
    if change_type == ChangeType.UPDATED and old_data == new_data:
        return

    ChangeLog.objects.create(
        change_type=change_type,
        object_type=obj.__class__.__name__,
        object_pid=obj.pid or cast(str, (old_data or {}).get("pid")),
        changes={"old": old_data, "new": new_data},
    )
