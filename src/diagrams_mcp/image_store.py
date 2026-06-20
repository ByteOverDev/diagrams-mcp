"""Temporary diagram output delivery stores."""

import json
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from mcp.types import EmbeddedResource

from diagrams_mcp.fastmcp_compat import Image, ToolError, binary_file

_FORMAT_MAP: dict[str, dict[str, str]] = {
    "png": {"mime": "image/png", "ext": ".png", "image_fmt": "png"},
    "svg": {"mime": "image/svg+xml", "ext": ".svg", "image_fmt": "svg+xml"},
    "pdf": {"mime": "application/pdf", "ext": ".pdf", "image_fmt": "pdf"},
}

# Anthropic's vision API accepts only PNG/JPEG/GIF/WebP for inline images and
# rejects payloads larger than ~5 MB. Sending SVG/PDF inline, or oversized PNGs,
# produces a 400 that poisons the conversation transcript for every follow-up
# turn — so we transparently promote those to a download link.
ANTHROPIC_INLINE_IMAGE_MAX_BYTES = 5 * 1024 * 1024
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImageEntry:
    """A stored diagram image with expiry metadata."""

    data: bytes
    filename: str
    expires_at: float
    fmt: str = field(default="png")


class ImageStore:
    """Thread-safe in-memory image store with automatic expiry and size caps.

    Follows FastMCP's TokenCache pattern: entries have an ``expires_at``
    timestamp, expired entries are deleted on access, and a sweep runs
    on each ``store()`` call to purge all stale entries.

    Size caps prevent memory exhaustion: ``max_entries`` limits the number
    of stored images, ``max_total_bytes`` caps aggregate memory usage, and
    ``max_entry_bytes`` rejects individual images that are too large.
    When a cap is reached, the entry with the earliest expiry is evicted.
    """

    DEFAULT_TTL: float = 900.0  # 15 minutes

    def __init__(
        self,
        *,
        max_entries: int = 100,
        max_total_bytes: int = 200 * 1024 * 1024,  # 200 MB
        max_entry_bytes: int = 10 * 1024 * 1024,  # 10 MB
    ) -> None:
        for name, value in [
            ("max_entries", max_entries),
            ("max_total_bytes", max_total_bytes),
            ("max_entry_bytes", max_entry_bytes),
        ]:
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
        self._entries: dict[str, ImageEntry] = {}
        self._lock = threading.Lock()
        self._total_bytes = 0
        self.max_entries = max_entries
        self.max_total_bytes = max_total_bytes
        self.max_entry_bytes = max_entry_bytes

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

        Raises:
            ValueError: If *data* exceeds ``max_entry_bytes`` or ``max_total_bytes``.
        """
        entry_size = len(data)
        if entry_size > self.max_entry_bytes:
            raise ValueError(
                f"Image too large: {entry_size} bytes exceeds {self.max_entry_bytes} byte limit"
            )
        if entry_size > self.max_total_bytes:
            raise ValueError(
                f"Image too large: {entry_size} bytes exceeds"
                f" {self.max_total_bytes} byte total-store limit"
            )
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sweep()
            # Evict oldest entries until the new entry fits within caps.
            while self._entries and (
                len(self._entries) >= self.max_entries
                or self._total_bytes + entry_size > self.max_total_bytes
            ):
                oldest_key = min(self._entries, key=lambda k: self._entries[k].expires_at)
                self._remove(oldest_key)
            self._entries[token] = ImageEntry(
                data=data,
                filename=filename,
                expires_at=time.time() + ttl,
                fmt=fmt,
            )
            self._total_bytes += entry_size
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
                self._remove(token)
                return None
            return entry

    def _remove(self, key: str) -> None:
        """Remove an entry and update the byte counter. Caller must hold _lock."""
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._total_bytes -= len(entry.data)

    def _sweep(self) -> None:
        """Remove all expired entries from the store. Caller must hold _lock."""
        now = time.time()
        expired = [k for k, v in self._entries.items() if v.expires_at < now]
        for k in expired:
            self._remove(k)


class ImageStorage(Protocol):
    """Storage interface for temporary rendered outputs."""

    max_entry_bytes: int

    def store(
        self, data: bytes, filename: str, *, fmt: str = "png", ttl: float = ImageStore.DEFAULT_TTL
    ) -> str: ...

    def get(self, token: str) -> ImageEntry | None: ...


class FileImageStore:
    """File-backed temporary output store that avoids retaining bytes in process memory."""

    DEFAULT_TTL: float = ImageStore.DEFAULT_TTL

    def __init__(self, root: str | os.PathLike[str], *, max_entry_bytes: int = 10 * 1024 * 1024):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_entry_bytes = max_entry_bytes
        self._lock = threading.Lock()

    def store(
        self, data: bytes, filename: str, *, fmt: str = "png", ttl: float = DEFAULT_TTL
    ) -> str:
        entry_size = len(data)
        if entry_size > self.max_entry_bytes:
            raise ValueError(
                f"Image too large: {entry_size} bytes exceeds {self.max_entry_bytes} byte limit"
            )
        token = secrets.token_urlsafe(32)
        meta = {
            "filename": filename,
            "fmt": fmt,
            "expires_at": time.time() + ttl,
        }
        with self._lock:
            self._sweep()
            (self.root / f"{token}.bin").write_bytes(data)
            (self.root / f"{token}.json").write_text(json.dumps(meta), encoding="utf-8")
        return token

    def get(self, token: str) -> ImageEntry | None:
        if not _is_token_safe(token):
            return None
        meta_path = self.root / f"{token}.json"
        data_path = self.root / f"{token}.bin"
        with self._lock:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta["expires_at"] < time.time():
                    self._remove(token)
                    return None
                data = data_path.read_bytes()
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                self._remove(token)
                return None
        return ImageEntry(
            data=data,
            filename=str(meta.get("filename", "image")),
            expires_at=float(meta["expires_at"]),
            fmt=str(meta.get("fmt", "png")),
        )

    def _remove(self, token: str) -> None:
        for suffix in (".bin", ".json"):
            try:
                (self.root / f"{token}{suffix}").unlink()
            except FileNotFoundError:
                pass

    def _sweep(self) -> None:
        now = time.time()
        for meta_path in self.root.glob("*.json"):
            token = meta_path.stem
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._remove(token)
                continue
            if meta.get("expires_at", 0) < now:
                self._remove(token)


def _is_token_safe(token: str) -> bool:
    return bool(token) and all(c.isalnum() or c in "-_" for c in token)


def _select_output_store() -> ImageStorage:
    store_dir = os.environ.get("DIAGRAMS_IMAGE_STORE_DIR", "").strip()
    if store_dir:
        return FileImageStore(store_dir)
    return image_store


image_store = ImageStore()
output_store: ImageStorage = _select_output_store()


def default_download_link() -> bool:
    """Default value for each render tool's ``download_link`` parameter.

    URLs work in every MCP client and never poison the transcript when a
    payload can't be decoded, so they are the default. Set
    ``DIAGRAMS_INLINE_DEFAULT=true`` (or ``1``/``yes``) to flip back to
    inline bytes for clients that prefer them.
    """
    flag = os.environ.get("DIAGRAMS_INLINE_DEFAULT", "").strip().lower()
    inline = flag in ("1", "true", "yes", "on")
    return not inline


def deliver_image(
    data: bytes,
    filename: str,
    download_link: bool,
    fmt: str = "png",
) -> Image | EmbeddedResource | str:
    """Return rendered image data as an inline Image/File or a temporary download link.

    Shared by render_diagram, render_mermaid, and render_plantuml.
    """
    if fmt not in _FORMAT_MAP:
        raise ValueError(f"Unknown format {fmt!r}. Supported: {', '.join(_FORMAT_MAP)}")

    # Validate PNG signature before any delivery decision so renderer bugs
    # are caught on both the inline and URL paths.
    if fmt == "png" and not data.startswith(_PNG_MAGIC):
        raise ToolError("Rendered PNG is malformed (missing PNG signature)")

    # Fail fast with one clear message when the payload can't be delivered by
    # any path: URLs are bounded by the active store's per-entry cap, and inline PNGs
    # are bounded by Anthropic's 5 MB vision cap.
    if len(data) > output_store.max_entry_bytes:
        raise ToolError(
            f"Rendered {fmt} is too large: {len(data)} bytes exceeds"
            f" {output_store.max_entry_bytes} byte delivery limit"
        )

    # Formats Claude's vision API cannot decode inline are always served via
    # download link, regardless of caller preference.
    if fmt != "png":
        download_link = True
    elif len(data) > ANTHROPIC_INLINE_IMAGE_MAX_BYTES:
        download_link = True

    if download_link:
        try:
            token = output_store.store(data, filename, fmt=fmt)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        base_url = os.environ.get("BASE_URL", "").rstrip("/")
        _logger.info(
            "output_delivery %s",
            json.dumps(
                {
                    "event": "output_stored",
                    "format": fmt,
                    "delivery": "download_link",
                    "bytes": len(data),
                    "store": type(output_store).__name__,
                },
                sort_keys=True,
            ),
        )
        return f"{base_url}/images/{token}"

    image_fmt = _FORMAT_MAP[fmt]["image_fmt"]
    _logger.info(
        "output_delivery %s",
        json.dumps(
            {
                "event": "output_inline",
                "format": fmt,
                "delivery": "inline",
                "bytes": len(data),
            },
            sort_keys=True,
        ),
    )
    if fmt == "pdf":
        return binary_file(data, f"{filename}.pdf", _FORMAT_MAP[fmt]["mime"])
    return Image(data=data, format=image_fmt)
