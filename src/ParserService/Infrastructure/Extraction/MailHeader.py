from enum import StrEnum


class MailHeader(StrEnum):
    """E-mail headers kept in the file properties of an EML or MSG result."""

    SUBJECT = "email_subject"
    FROM = "email_from"
    TO = "email_to"
    DATE = "email_date"
