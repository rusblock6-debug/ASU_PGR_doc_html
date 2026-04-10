from enum import StrEnum


class Permission(StrEnum):
    WORK_TIME_MAP = "work-time-map"
    WORK_ORDER = "work_order"
    TRIP_EDITOR = "trip_editor"
    PLACES = "places"
    SECTIONS = "sections"
    TAGS = "tags"
    EQUIPMENT = "equipment"
    HORIZONS = "horizons"
    DISPATCH_MAP = "dispatch_map"
    STATUSES = "statuses"
    CARGO = "cargo"
    MAP = "map"
    STAFF = "staff"
    ROLES = "roles"


class Action(StrEnum):
    VIEW = "view"
    EDIT = "edit"
