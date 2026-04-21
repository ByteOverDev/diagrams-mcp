import pytest
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.image_store import (
    ANTHROPIC_INLINE_IMAGE_MAX_BYTES,
    ImageStore,
    default_download_link,
    deliver_image,
    image_store,
)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_VALID_PNG = _PNG_MAGIC + b"fake-png-payload"


def test_store_and_retrieve():
    """Storing an image returns a token that retrieves the same data."""
    store = ImageStore()
    token = store.store(b"png-bytes", "my_diagram")
    entry = store.get(token)
    assert entry is not None
    assert entry.data == b"png-bytes"
    assert entry.filename == "my_diagram"


def test_get_unknown_token_returns_none():
    """Retrieving an unknown token returns None."""
    store = ImageStore()
    assert store.get("nonexistent-token") is None


def test_get_expired_entry_returns_none():
    """Retrieving an expired entry returns None and deletes it."""
    store = ImageStore()
    token = store.store(b"data", "file", ttl=0)
    # TTL=0 means it expires immediately
    assert store.get(token) is None
    # Entry should be deleted from internal dict
    assert token not in store._entries


def test_sweep_removes_expired_keeps_live():
    """_sweep() removes expired entries while keeping live ones."""
    store = ImageStore()
    expired_token = store.store(b"old", "old", ttl=0)
    live_token = store.store(b"new", "new", ttl=3600)
    # sweep runs inside store(), but let's call it explicitly to verify
    store._sweep()
    assert store.get(expired_token) is None
    assert store.get(live_token) is not None
    assert store.get(live_token).data == b"new"


def test_token_is_url_safe_string():
    """store() returns a URL-safe string token."""
    store = ImageStore()
    token = store.store(b"data", "file")
    # secrets.token_urlsafe(32) produces 43 chars
    assert isinstance(token, str)
    assert len(token) == 43
    # URL-safe: only alphanumeric, hyphens, underscores
    assert all(c.isalnum() or c in "-_" for c in token)


def test_multiple_stores_independent():
    """Multiple stored images are retrievable independently."""
    store = ImageStore()
    t1 = store.store(b"img1", "file1")
    t2 = store.store(b"img2", "file2")
    assert t1 != t2
    assert store.get(t1).data == b"img1"
    assert store.get(t2).data == b"img2"


def test_deliver_image_inline_default_png():
    """deliver_image returns an Image with format=png by default."""
    result = deliver_image(_VALID_PNG, "test", download_link=False)
    assert isinstance(result, Image)
    content = result.to_image_content()
    assert content.mimeType == "image/png"


def test_deliver_image_svg_auto_promotes_to_download_link():
    """SVG can never be an inline image for Claude, so it must be promoted."""
    result = deliver_image(b"<svg></svg>", "test", download_link=False, fmt="svg")
    assert isinstance(result, str)
    assert result.startswith("/images/") or "/images/" in result


def test_deliver_image_pdf_auto_promotes_to_download_link():
    """PDF is not a renderable inline image block, so it must be promoted."""
    result = deliver_image(b"%PDF-1.4 fake", "test", download_link=False, fmt="pdf")
    assert isinstance(result, str)
    assert "/images/" in result


def test_deliver_image_oversized_png_auto_promotes():
    """PNGs larger than Anthropic's inline cap are promoted to a download link."""
    big = _PNG_MAGIC + b"x" * (ANTHROPIC_INLINE_IMAGE_MAX_BYTES + 1 - len(_PNG_MAGIC))
    result = deliver_image(big, "big", download_link=False)
    assert isinstance(result, str)
    assert "/images/" in result


def test_deliver_image_rejects_malformed_png():
    """Malformed PNG bytes raise ToolError instead of poisoning the transcript."""
    with pytest.raises(ToolError, match="malformed"):
        deliver_image(b"not-a-png", "test", download_link=False)


def test_deliver_image_download_link_png():
    """deliver_image returns a /images/ path for download_link=True with default PNG."""
    result = deliver_image(_VALID_PNG, "test", download_link=True)
    assert isinstance(result, str)
    assert result.startswith("/images/")


def test_deliver_image_download_link_rejects_malformed_png():
    """Malformed PNG bytes are rejected even on the URL path, so renderer bugs surface early."""
    with pytest.raises(ToolError, match="malformed"):
        deliver_image(b"not-a-png", "test", download_link=True)


def test_deliver_image_download_link_svg():
    """deliver_image returns a /images/ path for download_link=True with fmt='svg'."""
    result = deliver_image(b"<svg></svg>", "test", download_link=True, fmt="svg")
    assert isinstance(result, str)
    assert result.startswith("/images/")


def test_deliver_image_download_link_pdf():
    """deliver_image returns a /images/ path for download_link=True with fmt='pdf'."""
    result = deliver_image(b"%PDF-1.4 fake", "test", download_link=True, fmt="pdf")
    assert isinstance(result, str)
    assert result.startswith("/images/")


def test_store_preserves_fmt():
    """ImageStore preserves the fmt field through store/get."""
    store = ImageStore()
    token = store.store(b"<svg></svg>", "test", fmt="svg")
    entry = store.get(token)
    assert entry is not None
    assert entry.fmt == "svg"


def test_deliver_image_download_link_with_base_url(monkeypatch):
    """deliver_image prepends BASE_URL to download links when set."""
    monkeypatch.setenv("BASE_URL", "https://example.up.railway.app")
    result = deliver_image(_VALID_PNG, "test", download_link=True)
    assert isinstance(result, str)
    assert result.startswith("https://example.up.railway.app/images/")


def test_deliver_image_download_link_base_url_trailing_slash(monkeypatch):
    """deliver_image strips trailing slash from BASE_URL to avoid double slashes."""
    monkeypatch.setenv("BASE_URL", "https://example.up.railway.app/")
    result = deliver_image(_VALID_PNG, "test", download_link=True)
    assert "//" not in result.split("://")[1]


def test_deliver_image_rejects_unknown_fmt():
    """deliver_image raises ValueError for an unknown format."""
    with pytest.raises(ValueError, match="Unknown format"):
        deliver_image(b"data", "test", download_link=False, fmt="bmp")


# --- Size cap tests ---


def test_store_rejects_oversized_entry():
    """store() raises ValueError when a single entry exceeds max_entry_bytes."""
    store = ImageStore(max_entry_bytes=100)
    with pytest.raises(ValueError, match="too large"):
        store.store(b"x" * 101, "big")


def test_store_accepts_entry_at_exact_limit():
    """store() accepts an entry whose size equals max_entry_bytes."""
    store = ImageStore(max_entry_bytes=100)
    token = store.store(b"x" * 100, "exact")
    assert store.get(token) is not None


def test_store_evicts_oldest_when_max_entries_reached():
    """When max_entries is reached, the entry with earliest expires_at is evicted."""
    store = ImageStore(max_entries=2, max_total_bytes=10_000_000)
    t1 = store.store(b"a", "f1", ttl=100)
    t2 = store.store(b"b", "f2", ttl=200)
    t3 = store.store(b"c", "f3", ttl=300)  # should evict t1
    assert store.get(t1) is None
    assert store.get(t2) is not None
    assert store.get(t3) is not None


def test_store_evicts_to_fit_within_max_total_bytes():
    """Entries are evicted until total bytes plus new entry fit within max_total_bytes."""
    store = ImageStore(max_total_bytes=200, max_entry_bytes=200)
    t1 = store.store(b"x" * 80, "f1", ttl=100)
    t2 = store.store(b"y" * 80, "f2", ttl=200)
    # Total is 160. Adding 80 more would be 240 > 200, so t1 is evicted.
    t3 = store.store(b"z" * 80, "f3", ttl=300)
    assert store.get(t1) is None
    assert store.get(t2) is not None
    assert store.get(t3) is not None


def test_total_bytes_updated_on_sweep():
    """_total_bytes is accurately decremented when expired entries are swept."""
    store = ImageStore(max_total_bytes=500, max_entry_bytes=500)
    store.store(b"x" * 100, "expired", ttl=0)
    # After next store, sweep runs first and frees 100 bytes
    t2 = store.store(b"y" * 100, "live", ttl=3600)
    assert store._total_bytes == 100
    assert store.get(t2) is not None


def test_total_bytes_updated_on_lazy_delete():
    """_total_bytes is decremented when get() lazy-deletes an expired entry."""
    store = ImageStore()
    store.store(b"x" * 50, "expired", ttl=0)
    assert store._total_bytes == 50
    # get() will lazy-delete the expired entry
    token = next(iter(store._entries))
    store.get(token)
    assert store._total_bytes == 0


def test_deliver_image_raises_tool_error_for_oversized(monkeypatch):
    """deliver_image raises ToolError when image exceeds store's max_entry_bytes."""
    monkeypatch.setattr(image_store, "max_entry_bytes", 100)
    with pytest.raises(ToolError, match="too large"):
        deliver_image(_PNG_MAGIC + b"x" * 101, "big", download_link=True)


def test_deliver_image_inline_rejects_over_entry_cap(monkeypatch):
    """Inline delivery is also bounded by max_entry_bytes for a consistent ceiling."""
    monkeypatch.setattr(image_store, "max_entry_bytes", 10)
    with pytest.raises(ToolError, match="too large"):
        deliver_image(_VALID_PNG, "test", download_link=False)


# --- DIAGRAMS_INLINE_DEFAULT env var ---


def test_default_download_link_defaults_to_true(monkeypatch):
    monkeypatch.delenv("DIAGRAMS_INLINE_DEFAULT", raising=False)
    assert default_download_link() is True


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", "Yes"])
def test_default_download_link_env_opts_into_inline(monkeypatch, value):
    monkeypatch.setenv("DIAGRAMS_INLINE_DEFAULT", value)
    assert default_download_link() is False


@pytest.mark.parametrize("value", ["false", "0", "no", "", "anything-else"])
def test_default_download_link_env_falsy_keeps_url_default(monkeypatch, value):
    monkeypatch.setenv("DIAGRAMS_INLINE_DEFAULT", value)
    assert default_download_link() is True
