"""Computation of the Italian public holidays that drive the year planner.

Only the rule-based entries live here: everything the centre decides year by
year (closures, granted days) is added by hand in the data file for that year.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


# Entry kinds, in the order they are stacked in a cell.
KIND_HOLIDAY = "H"      # office closed, red "H" marker
KIND_CLOSURE = "HC"     # holiday closure taken in advance/in lieu
KIND_GRANT = "grant"    # director's grant, extra day
KIND_NOTE = "note"      # labelled but still a working day


@dataclass
class Entry:
    date: dt.date
    label: str
    kind: str = KIND_HOLIDAY
    # Free-form note kept next to the label, e.g. "(in lieu of 1 May)".
    qualifier: str = ""
    # True when the generator produced it, False when a human typed it in.
    generated: bool = field(default=True, compare=False)

    @property
    def closed(self) -> bool:
        """Whether the centre is closed on that day."""
        return self.kind in (KIND_HOLIDAY, KIND_CLOSURE, KIND_GRANT)


def easter_sunday(year: int) -> dt.date:
    """Gregorian Easter (anonymous / Meeus-Jones-Butcher algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


# Fixed-date Italian public holidays, in calendar order.
FIXED_HOLIDAYS: list[tuple[int, int, str]] = [
    (1, 1, "New Year's Day"),
    (1, 6, "Epiphany"),
    (4, 25, "Liberation Day"),
    (5, 1, "Labour Day"),
    (6, 2, "Italian Nat'l Day"),
    (8, 15, "Assumption Day"),
    (11, 1, "All Saints' Day"),
    (12, 8, "Immaculate Conception"),
    (12, 25, "Christmas"),
    (12, 26, "St Stephen's Day"),
]


def statutory_entries(year: int) -> list[Entry]:
    """The public holidays that can be derived from the calendar alone.

    A holiday landing on a Saturday or a Sunday stays on its own date as a
    label without the "H" marker: the day taken in lieu is a decision of the
    centre, so it is left for the data file (see `pending_in_lieu`).
    """
    entries = [
        Entry(dt.date(year, month, day), label, KIND_HOLIDAY)
        for month, day, label in FIXED_HOLIDAYS
    ]
    easter = easter_sunday(year)
    entries.append(Entry(easter - dt.timedelta(days=2), "Good Friday", KIND_NOTE))
    entries.append(Entry(easter + dt.timedelta(days=1), "Easter Monday", KIND_HOLIDAY))

    for entry in entries:
        if entry.kind == KIND_HOLIDAY and entry.date.weekday() >= 5:
            entry.kind = KIND_NOTE

    entries.sort(key=lambda e: e.date)
    return entries


def pending_in_lieu(entries: list[Entry]) -> list[Entry]:
    """Statutory holidays that fell on a weekend and still need a day in lieu."""
    return [
        e
        for e in entries
        if e.kind == KIND_NOTE and e.date.weekday() >= 5 and e.label != "Good Friday"
    ]
