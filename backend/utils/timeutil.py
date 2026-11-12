"""UTC timestamps shared by the database and the API."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def utc_iso(moment: datetime | None = None) -> str:
    value = as_utc(moment or utc_now())
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
