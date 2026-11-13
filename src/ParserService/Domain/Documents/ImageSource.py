from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageSource:
    """Where an image comes from and its declared size (schema 1.2).

    ``source`` is the image reference as written in the file, such as a relative
    path or URL; it is never fetched. ``width`` and ``height`` are the declared
    size in pixels, when the file states one.
    """

    source: str | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if self.source is not None and not self.source.strip():
            message = "image source must not be blank"
            raise ValueError(message)
        for size in (self.width, self.height):
            if size is not None and size < 1:
                message = "image width and height are counted from 1"
                raise ValueError(message)
