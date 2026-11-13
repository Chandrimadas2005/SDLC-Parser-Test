import dataclasses

from ParserService.Domain.Documents.DocumentStatus import DocumentStatus
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Infrastructure.Extraction.BundleSection import BundleSection
from ParserService.Infrastructure.Extraction.DocumentBundle import DocumentBundle
from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile
from ParserService.Infrastructure.Extraction.EmbeddedFileParser import EmbeddedFileParser
from ParserService.Infrastructure.Extraction.HtmlText import HtmlText
from ParserService.Infrastructure.Extraction.MailContent import MailContent


class MailAssembler:
    """Builds the result of an e-mail: the body first, then every attachment.

    The body is the plain-text part when there is one; otherwise the HTML part,
    parsed by the HTML extractor when it is installed, or turned into plain text.
    Attachments are parsed like uploads. Headers go into the file properties.
    """

    BODY_TITLE = "Message body"

    def __init__(self, files: EmbeddedFileParser, bundle: DocumentBundle) -> None:
        self._files = files
        self._bundle = bundle

    def build(self, request: ExtractionRequest, mail: MailContent) -> ParsedDocument:
        """Build the result.

        Args:
            request: The e-mail file, its facts and its detection.
            mail: What was read from it.

        Returns:
            The parsed document.
        """
        sections = [self._body(mail)]
        sections += [BundleSection(a.name, self._files.parse(a)) for a in mail.attachments]
        document = self._bundle.build(request, sections)
        headers = {str(key): value for key, value in mail.headers.items() if value}
        facts = document.facts
        facts = dataclasses.replace(facts, properties={**(facts.properties or {}), **headers})
        return dataclasses.replace(document, facts=facts)

    def _body(self, mail: MailContent) -> BundleSection:
        if mail.text is None and mail.html is not None:
            parsed = self._files.parse(EmbeddedFile("body.html", mail.html.encode()))
            if parsed.is_ok and parsed.unwrap().status is DocumentStatus.SUCCEEDED:
                return BundleSection(self.BODY_TITLE, parsed)
        text = mail.text if mail.text is not None else HtmlText().plain(mail.html or "")
        body = EmbeddedFile("body.txt", text.encode())
        return BundleSection(self.BODY_TITLE, self._files.parse(body))
