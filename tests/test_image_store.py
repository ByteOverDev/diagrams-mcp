from diagrams_mcp.image_store import ImageStore


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
