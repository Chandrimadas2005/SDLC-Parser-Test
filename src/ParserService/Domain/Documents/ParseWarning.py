from dataclasses import dataclass

from ParserService.Domain.Documents.Locator import Locator
from ParserService.Domain.Documents.WarningCode import WarningCode


@dataclass(frozen=True, slots=True)
class ParseWarning:
    """Something that was skipped, guessed or repaired, and where (brief, section 2.2).

    The locator is ``None`` only when the warning concerns the whole file, such as
    an extension that does not match the real type.
    """

    code: WarningCode
    locator: Locator | None = None
