"""Reading and writing the per-year file that describes a planner.

The file is TOML, which the standard library reads on its own: no package has
to be installed for the sheet to be printed.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError as missing:     # Python 3.10 and older
    raise SystemExit(
        "this needs Python 3.11 or newer, which reads TOML on its own"
    ) from missing

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

COLOUR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")

DEFAULT_HEADER = {
    "organization": "Science and Technology Organization",
    "centre": "Centre for Maritime Research and Experimentation",
    "url": "http://www.cmre.nato.int",
    "background": "#6c9adb",
    "year_colour": "#c00000",
    "year_background": "#ffffff",
    "year_border": "",
    "rule_colour": "",
    "cell_colour": "",
    "weekend_colour": "",
    "logo": "",
}


@dataclass
class Footnote:
    """A line under the grid, with a look of its own."""

    text: str
    colour: str = ""        # empty takes the sheet's own ink
    bold: bool = False


@dataclass
class Planner:
    year: int
    header: dict = field(default_factory=lambda: dict(DEFAULT_HEADER))
    entries: list[Entry] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)

    def by_date(self) -> dict[dt.date, Entry]:
        return {e.date: e for e in self.entries}


def draft(year: int) -> Planner:
    """A starting point for a new year: statutory holidays only."""
    return Planner(year=year, entries=statutory_entries(year))


def _as_date(value) -> dt.date:
    """TOML gives back a date of its own; a quoted one is read here."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value.strip())
    raise ValueError(f"{value!r} is not a date I can read")


def load(path: Path) -> Planner:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    year = int(raw["year"])
    header = dict(DEFAULT_HEADER)
    header.update(raw.get("header") or {})

    for field_name in ("background", "year_colour", "year_background", "year_border",
                       "rule_colour", "cell_colour", "weekend_colour"):
        _check_colour(path, field_name, header.get(field_name, ""))

    entries: list[Entry] = []
    seen: dict[dt.date, Entry] = {}
    for item in raw.get("holidays") or []:
        date = _as_date(item["date"])
        if date.year != year:
            raise ValueError(f"{path.name}: {date} does not belong to {year}")

        kind = str(item.get("kind", KIND_HOLIDAY))
        if kind not in VALID_KINDS:
            raise ValueError(
                f"{path.name}: unknown kind {kind!r} on {date} "
                f"(use one of {', '.join(VALID_KINDS)})"
            )

        if date in seen:
            raise ValueError(
                f"{path.name}: two entries on {date} "
                f"({seen[date].label!r} and {item['label']!r}); "
                "merge them into one label"
            )

        entry = Entry(
            date=date,
            label=str(item["label"]),
            kind=kind,
            qualifier=str(item.get("qualifier", "")),
            generated=False,
        )
        seen[date] = entry
        entries.append(entry)

    entries.sort(key=lambda e: e.date)
    return Planner(
        year=year,
        header=header,
        entries=entries,
        footnotes=[_as_footnote(path, item) for item in raw.get("footnotes") or []],
    )


def _check_colour(path: Path, field_name: str, value) -> None:
    """Colours are checked as they are read, not left to surface as a bad sheet."""
    colour = str(value or "")
    if colour and not COLOUR.fullmatch(colour):
        raise ValueError(
            f"{path.name}: {field_name} is {colour!r}; it wants a colour "
            'written like "#c00000", or "" for none'
        )


def _as_footnote(path: Path, item) -> Footnote:
    """A footnote is a bare line of text, or a line with a look of its own."""
    if isinstance(item, str):
        return Footnote(text=item)
    if not isinstance(item, dict) or "text" not in item:
        raise ValueError(
            f"{path.name}: a footnote is a string, or a table with a text field, "
            f"not {item!r}"
        )
    _check_colour(path, "a footnote colour", item.get("colour", ""))
    return Footnote(
        text=str(item["text"]),
        colour=str(item.get("colour", "")),
        bold=bool(item.get("bold", False)),
    )


_TEMPLATE = """\
# Holiday planner for {year}.
#
# The holidays below were worked out from the calendar; everything the centre
# decides (closures, extra days, grants) has to be added by hand.
# kind: "H" = closed, red marker | "HC" = holiday closure | "grant" = granted day
#       "note" = labelled but still a working day
# qualifier: the small print beside the label, e.g. "(in lieu of 1 May)"

year = {year}

# Lines under the grid. A bare string, or a table when it wants a look of its
# own, for example:
#   footnotes = [
#     {{ text = "H = centre closed", colour = "#c00000", bold = true }},
#     "HC = holiday closure",
#   ]
footnotes = []

[header]
organization = {organization}
centre = {centre}
url = {url}
background = {background}     # "#ffffff" to print on a white sheet
year_colour = {year_colour}   # the digits of the year, top right
year_background = {year_background}   # the plaque they sit on
year_border = {year_border}           # a hairline round it, "" for none
rule_colour = {rule_colour}      # the lines between the day cells
cell_colour = {cell_colour}      # the fill of a working day
weekend_colour = {weekend_colour}   # the fill of a Saturday or a Sunday
logo = {logo}

{holidays}"""


def _scalar(value: str) -> str:
    """A TOML basic string: quoted, with the two characters that need it escaped."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump(planner: Planner, path: Path) -> None:
    blocks = []
    for entry in planner.entries:
        lines = [
            "[[holidays]]",
            f"date = {entry.date.isoformat()}   # {entry.date:%a}",
            f"label = {_scalar(entry.label)}",
            f"kind = {_scalar(entry.kind)}",
        ]
        if entry.qualifier:
            lines.append(f"qualifier = {_scalar(entry.qualifier)}")
        blocks.append("\n".join(lines))

    text = _TEMPLATE.format(
        year=planner.year,
        holidays="\n\n".join(blocks) + "\n",
        **{k: _scalar(v) for k, v in planner.header.items()},
    )
    path.write_text(text, encoding="utf-8")


def todo(planner: Planner) -> list[str]:
    """Human-readable reminders of what still has to be decided by hand."""
    messages = []
    for entry in pending_in_lieu(planner.entries):
        messages.append(
            # "%-d" and friends are a glibc extension that Windows rejects,
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
