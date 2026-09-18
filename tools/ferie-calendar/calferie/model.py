"""Reading and writing the per-year YAML file that describes a planner."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .holidays import (
    KIND_CLOSURE,
    KIND_GRANT,
    KIND_HOLIDAY,
    KIND_NOTE,
    Entry,
    pending_in_lieu,
    statutory_entries,
)

VALID_KINDS = (KIND_HOLIDAY, KIND_CLOSURE, KIND_GRANT, KIND_NOTE)

DEFAULT_HEADER = {
    "organization": "Science and Technology Organization",
    "centre": "Centre for Maritime Research and Experimentation",
    "url": "http://www.cmre.nato.int",
    "background": "#8e9aab",
    "logo_left": "assets/logo-placeholder.svg",
    "logo_right": "",
}


@dataclass
class Planner:
    year: int
    header: dict = field(default_factory=lambda: dict(DEFAULT_HEADER))
    entries: list[Entry] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)

    def by_date(self) -> dict[dt.date, Entry]:
        return {e.date: e for e in self.entries}


def draft(year: int) -> Planner:
    """A starting point for a new year: statutory holidays only."""
    return Planner(year=year, entries=statutory_entries(year))


def _as_date(value, year: int) -> dt.date:
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value.strip())
    raise ValueError(f"{value!r} is not a date I can read")


def load(path: Path) -> Planner:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    year = int(raw["year"])
    header = dict(DEFAULT_HEADER)
    header.update(raw.get("header") or {})

    entries: list[Entry] = []
    for item in raw.get("holidays") or []:
        date = _as_date(item["date"], year)
        if date.year != year:
            raise ValueError(f"{path.name}: {date} does not belong to {year}")
        kind = str(item.get("kind", KIND_HOLIDAY))
        if kind not in VALID_KINDS:
            raise ValueError(
                f"{path.name}: unknown kind {kind!r} on {date} "
                f"(use one of {', '.join(VALID_KINDS)})"
            )
        entries.append(
            Entry(
                date=date,
                label=str(item["label"]),
                kind=kind,
                qualifier=str(item.get("qualifier", "")),
                generated=False,
            )
        )

    seen: dict[dt.date, Entry] = {}
    for entry in entries:
        if entry.date in seen:
            raise ValueError(
                f"{path.name}: two entries on {entry.date} "
                f"({seen[entry.date].label!r} and {entry.label!r}); "
                "merge them into one label"
            )
        seen[entry.date] = entry

    entries.sort(key=lambda e: e.date)
    return Planner(
        year=year,
        header=header,
        entries=entries,
        footnotes=list(raw.get("footnotes") or []),
    )


_TEMPLATE = """\
# Holiday planner for {year}.
#
# Statutory holidays below were computed from the calendar; everything the
# centre decides (closures, extra days, grants) has to be added by hand.
# kind: H = closed, red marker | HC = holiday closure | grant = granted day
#       note = labelled but still a working day
# qualifier: the small print next to the label, e.g. "(in lieu of 1 May)"

year: {year}

header:
  organization: {organization}
  centre: {centre}
  url: {url}
  background: {background}
  logo_left: {logo_left}
  logo_right: {logo_right}

holidays:
{holidays}
footnotes: []
"""


def _scalar(value: str) -> str:
    """A YAML double-quoted scalar; JSON string syntax is a subset of it."""
    return json.dumps(str(value), ensure_ascii=False)


def dump(planner: Planner, path: Path) -> None:
    lines = []
    for entry in planner.entries:
        lines.append(f"  - date: {entry.date.isoformat()}   # {entry.date:%a}")
        lines.append(f"    label: {_scalar(entry.label)}")
        lines.append(f"    kind: {entry.kind}")
        if entry.qualifier:
            lines.append(f"    qualifier: {_scalar(entry.qualifier)}")
    text = _TEMPLATE.format(
        year=planner.year,
        holidays="\n".join(lines) + "\n",
        **{k: _scalar(v) for k, v in planner.header.items()},
    )
    path.write_text(text, encoding="utf-8")


def todo(planner: Planner) -> list[str]:
    """Human-readable reminders of what still has to be decided by hand."""
    messages = []
    for entry in pending_in_lieu(planner.entries):
        messages.append(
            # %-d and friends are a glibc extension that Windows rejects,
            # so the day number is formatted by hand.
            f"{entry.date.day} {entry.date:%b} ({entry.date:%A}) {entry.label}: "
            "falls on a weekend, a day in lieu has to be chosen"
        )
    if not any(e.kind in (KIND_CLOSURE, KIND_GRANT) for e in planner.entries):
        messages.append(
            "no holiday closure (HC) or granted day is listed yet, "
            "add the ones agreed for this year"
        )
    return messages
