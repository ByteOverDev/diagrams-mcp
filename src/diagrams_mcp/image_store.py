"""In-memory store for temporary diagram images with TTL-based expiry."""

import os
import secrets
import threading
import time
from dataclasses import dataclass, field

from fastmcp.utilities.types import File, Image

_FORMAT_MAP: dict[str, dict[str, str]] = {
    "png": {"mime": "image/png", "ext": ".png", "image_fmt": "png"},
    "svg": {"mime": "image/svg+xml", "ext": ".svg", "image_fmt": "svg+xml"},
    "pdf": {"mime": "application/pdf", "ext": ".pdf", "image_fmt": "pdf"},
}


@dataclass(slots=True)
class ImageEntry:
    """A stored diagram image with expiry metadata."""

    data: bytes
    filename: str
    expires_at: float
    fmt: str = field(default="png")


class ImageStore:
    """Thread-safe in-memory image store with automatic expiry.

    Follows FastMCP's TokenCache pattern: entries have an ``expires_at``
    timestamp, expired entries are deleted on access, and a sweep runs
    on each ``store()`` call to purge all stale entries.
    """

    DEFAULT_TTL: float = 900.0  # 15 minutes

    def __init__(self) -> None:
        self._entries: dict[str, ImageEntry] = {}
        self._lock = threading.Lock()

    def store(
        self, data: bytes, filename: str, *, fmt: str = "png", ttl: float = DEFAULT_TTL
    ) -> str:
        """Store image data and return an unguessable URL-safe token.

        Args:
            data: Raw image/document bytes.
            filename: Original filename (without extension).
            fmt: Output format key (``"png"``, ``"svg"``, or ``"pdf"``).
            ttl: Time-to-live in seconds. Defaults to 15 minutes.

        Returns:
            A URL-safe token string (43 characters, 256 bits of entropy).
        """
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sweep()
            self._entries[token] = ImageEntry(
                data=data,
                filename=filename,
                expires_at=time.time() + ttl,
                fmt=fmt,
            )
        return token

    def get(self, token: str) -> ImageEntry | None:
        """Retrieve an image entry by token, or None if missing/expired.

        Expired entries are deleted on access (lazy cleanup).
        """
        with self._lock:
            entry = self._entries.get(token)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                del self._entries[token]
                return None
            return entry

    def _sweep(self) -> None:
        """Remove all expired entries from the store. Caller must hold _lock."""
        now = time.time()
        expired = [k for k, v in self._entries.items() if v.expires_at < now]
        for k in expired:
            del self._entries[k]


image_store = ImageStore()


def deliver_image(
    data: bytes,
    filename: str,
    download_link: bool,
    fmt: str = "png",
) -> Image | File | str:
    """Return rendered image data as an inline Image/File or a temporary download link.

    Shared by render_diagram, render_mermaid, and render_plantuml.
    """
    if fmt not in _FORMAT_MAP:
        raise ValueError(f"Unknown format {fmt!r}. Supported: {', '.join(_FORMAT_MAP)}")

    if download_link:
        token = image_store.store(data, filename, fmt=fmt)
        base_url = os.environ.get("BASE_URL", "").rstrip("/")
        return f"{base_url}/images/{token}"

    if fmt == "pdf":
        return File(data=data, format="pdf")

    image_fmt = _FORMAT_MAP[fmt]["image_fmt"]
    return Image(data=data, format=image_fmt)
