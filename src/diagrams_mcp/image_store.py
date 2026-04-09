"""In-memory store for temporary diagram images with TTL-based expiry."""

import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from fastmcp.utilities.types import Image


@dataclass(slots=True)
class ImageEntry:
    """A stored diagram image with expiry metadata."""

    data: bytes
    filename: str
    expires_at: float


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

    def store(self, data: bytes, filename: str, ttl: float = DEFAULT_TTL) -> str:
        """Store image data and return an unguessable URL-safe token.

        Args:
            data: Raw PNG bytes.
            filename: Original filename (without extension).
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
    png_data: bytes,
    filename: str,
    output_path: str | None,
    download_link: bool,
) -> Image | str:
    """Return rendered PNG data as an inline Image, download link, or saved file.

    Shared by render_diagram, render_mermaid, and render_plantuml.
    """
    if output_path:
        base_dir = Path(output_path).expanduser().resolve()
        if base_dir.is_dir():
            safe_name = Path(filename).name
            if not safe_name or safe_name.startswith("."):
                safe_name = "diagram"
            dest = (base_dir / f"{safe_name}.png").resolve()
            if not str(dest).startswith(str(base_dir) + os.sep) and dest.parent != base_dir:
                raise ValueError(
                    f"Invalid filename {filename!r}: resolves outside the output directory."
                )
        else:
            dest = base_dir
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png_data)
        return f"Diagram saved to {dest}"

    if download_link:
        token = image_store.store(png_data, filename)
        return f"/images/{token}"

    return Image(data=png_data, format="png")
