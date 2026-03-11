from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DocumentItem:
    url: str
    normalized_url: str
    page_type: str
    title: str | None = None
    text: str | None = None
    html: str | None = None
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None
    fetched_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class ImageAssetItem:
    url: str
    normalized_url: str
    page_type: str
    title: str | None = None
    text: str | None = None
    html: str | None = None
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None
    fetched_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class RawPageItem:
    url: str
    normalized_url: str
    page_type: str
    title: str | None = None
    text: str | None = None
    html: str | None = None
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None
    fetched_at: str = field(default_factory=utc_now_iso)
