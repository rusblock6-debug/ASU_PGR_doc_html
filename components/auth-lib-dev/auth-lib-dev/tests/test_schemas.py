import pytest
from pydantic import ValidationError

from auth_lib.schemas import PermissionSchema, RoleSchema, UserPayload
from tests.conftest import SAMPLE_PAYLOAD


def test_permission_schema_parses_valid_data():
    data = {"id": 1, "name": "work_order", "can_view": True, "can_edit": False}
    perm = PermissionSchema.model_validate(data)
    assert perm.id == 1
    assert perm.name == "work_order"
    assert perm.can_view is True
    assert perm.can_edit is False


def test_role_schema_with_permissions_list():
    data = {
        "id": 1,
        "name": "admin",
        "permissions": [
            {"id": 1, "name": "work_order", "can_view": True, "can_edit": True},
        ],
    }
    role = RoleSchema.model_validate(data)
    assert role.name == "admin"
    assert len(role.permissions) == 1
    assert role.permissions[0].name == "work_order"


def test_user_payload_full_parse():
    user = UserPayload.model_validate(SAMPLE_PAYLOAD)
    assert user.id == 1
    assert user.username == "testuser"
    assert user.role.name == "admin"
    assert len(user.role.permissions) == 2


def test_user_payload_missing_field_raises():
    incomplete = {"id": 1, "role": {"id": 1, "name": "x", "permissions": []}, "exp": 123}
    with pytest.raises(ValidationError):
        UserPayload.model_validate(incomplete)


def test_user_payload_nested_access():
    user = UserPayload.model_validate(SAMPLE_PAYLOAD)
    assert user.role.permissions[0].can_view is True
    assert user.role.permissions[1].name == "work-time-map"
