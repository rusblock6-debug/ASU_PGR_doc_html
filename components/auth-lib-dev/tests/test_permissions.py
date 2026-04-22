import pytest

from auth_lib.permissions import Permission, Action


EXPECTED_VALUES = {
    "WORK_TIME_MAP": "work-time-map",
    "WORK_ORDER": "work_order",
    "TRIP_EDITOR": "trip_editor",
    "PLACES": "places",
    "SECTIONS": "sections",
    "TAGS": "tags",
    "EQUIPMENT": "equipment",
    "HORIZONS": "horizons",
    "DISPATCH_MAP": "dispatch_map",
    "STATUSES": "statuses",
    "CARGO": "cargo",
    "MAP": "map",
    "STAFF": "staff",
    "ROLES": "roles",
}


def test_permission_enum_has_14_members():
    assert len(Permission) == 14


@pytest.mark.parametrize("name,value", EXPECTED_VALUES.items())
def test_permission_values_match_jwt_strings(name, value):
    member = Permission[name]
    assert member.value == value


def test_work_time_map_uses_hyphens():
    assert "-" in Permission.WORK_TIME_MAP.value
    assert Permission.WORK_TIME_MAP.value == "work-time-map"


def test_action_enum_values():
    assert Action.VIEW.value == "view"
    assert Action.EDIT.value == "edit"


def test_permission_is_str_enum():
    assert isinstance(Permission.WORK_ORDER, str)
    assert isinstance(Action.VIEW, str)


def test_not_authenticated_raises_401():
    from auth_lib.exceptions import NotAuthenticated

    exc = NotAuthenticated()
    assert exc.status_code == 401
    assert exc.detail == "Not authenticated"


def test_not_authenticated_custom_detail():
    from auth_lib.exceptions import NotAuthenticated

    exc = NotAuthenticated(detail="Custom msg")
    assert exc.status_code == 401
    assert exc.detail == "Custom msg"


def test_permission_denied_raises_403():
    from auth_lib.exceptions import PermissionDenied

    exc = PermissionDenied()
    assert exc.status_code == 403
    assert exc.detail == "Permission denied"


def test_permission_denied_custom_detail():
    from auth_lib.exceptions import PermissionDenied

    exc = PermissionDenied(detail="No access")
    assert exc.status_code == 403
    assert exc.detail == "No access"
