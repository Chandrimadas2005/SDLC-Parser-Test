from enum import StrEnum


class PropertyName(StrEnum):
    """Keys of ``DocumentFacts.properties``: the file's own metadata (brief, section 2.2).

    Office core and extended properties come from the file itself; ``encoding``,
    ``delimiter``, ``codepage`` and ``biff_version`` describe how the file was read.
    """

    TITLE = "title"
    SUBJECT = "subject"
    CREATOR = "creator"
    KEYWORDS = "keywords"
    DESCRIPTION = "description"
    CATEGORY = "category"
    CONTENT_STATUS = "content_status"
    IDENTIFIER = "identifier"
    LANGUAGE = "language"
    VERSION = "version"
    REVISION = "revision"
    LAST_MODIFIED_BY = "last_modified_by"
    CREATED = "created"
    MODIFIED = "modified"
    LAST_PRINTED = "last_printed"
    APPLICATION = "application"
    APP_VERSION = "app_version"
    COMPANY = "company"
    MANAGER = "manager"
    ENCODING = "encoding"
    DELIMITER = "delimiter"
    CODEPAGE = "codepage"
    BIFF_VERSION = "biff_version"
