"""Stable, non-personal identifiers for Dietly entities."""

from __future__ import annotations

import hashlib


def entity_namespace(unique_id: str | None, entry_id: str) -> str:
    """Return a persistent opaque namespace for entity and device IDs."""
    source = unique_id or entry_id
    return hashlib.sha256(source.encode()).hexdigest()[:20]
