import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Final

import structlog

from ParserService.Infrastructure.Http.HttpHeader import HttpHeader
from ParserService.Infrastructure.Logging.LogField import LogField

Scope = MutableMapping[str, object]
Message = MutableMapping[str, object]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
App = Callable[[Scope, Receive, Send], Awaitable[None]]


class RequestIdMiddleware:
    """Gives every request an ID: taken from ``X-Request-ID`` or generated.

    The ID is stored in the ASGI scope for routes, echoed in the response header, and
    bound to the structlog context so every log line of the request carries it.
    """

    SCOPE_KEY: Final = "request_id"
    HTTP_SCOPE_TYPE: Final = "http"
    RESPONSE_START: Final = "http.response.start"

    def __init__(self, app: App) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI connection.

        Args:
            scope: The ASGI connection scope.
            receive: Awaitable that yields incoming messages.
            send: Awaitable that sends outgoing messages.
        """
        if scope.get("type") != self.HTTP_SCOPE_TYPE:
            await self._app(scope, receive, send)
            return
        request_id = self._incoming_id(scope) or str(uuid.uuid4())
        scope[self.SCOPE_KEY] = request_id
        structlog.contextvars.bind_contextvars(**{LogField.REQUEST_ID.value: request_id})
        try:
            await self._app(scope, receive, self._sender_with_header(send, request_id))
        finally:
            structlog.contextvars.unbind_contextvars(LogField.REQUEST_ID.value)

    def _incoming_id(self, scope: Scope) -> str | None:
        wanted = HttpHeader.REQUEST_ID.lower().encode()
        headers = scope.get("headers")
        if not isinstance(headers, list):
            return None
        for name, value in headers:
            if isinstance(name, bytes) and name.lower() == wanted and isinstance(value, bytes):
                return value.decode("latin-1")[:128] or None
        return None

    def _sender_with_header(self, send: Send, request_id: str) -> Send:
        name = HttpHeader.REQUEST_ID.lower().encode()
        header = (name, request_id.encode("latin-1"))

        async def send_with_header(message: Message) -> None:
            if message.get("type") == self.RESPONSE_START:
                headers = message.setdefault("headers", [])
                if isinstance(headers, list) and not any(key.lower() == name for key, _ in headers):
                    headers.append(header)
            await send(message)

        return send_with_header
