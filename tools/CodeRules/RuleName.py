from enum import StrEnum


class RuleName(StrEnum):
    """Codes of the repository code rules that ruff cannot check on its own."""

    METHOD_LENGTH = "CR001"
    TRY_PER_METHOD = "CR002"
    TOP_LEVEL_FUNCTION = "CR003"
    ONE_PUBLIC_CLASS = "CR004"
    FILE_NAME_MATCHES_CLASS = "CR005"
    PACKAGE_INIT = "CR006"
    PACKAGE_ALL = "CR007"
    FORBIDDEN_PACKAGE = "CR008"
