"""The geometry of the planner: twelve month rows sharing one weekday grid.

Each month is a row of days running left to right, shifted right by the weekday
of its first day, so a given column always holds the same weekday and a week
reads as a vertical slice of the sheet. The longest possible row, a 31-day
month starting on a Sunday, needs 6 + 31 = 37 columns.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass

COLUMNS = 37
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@dataclass
class Cell:
    date: dt.date | None = None
    label: str = ""
    qualifier: str = ""
    marker: str = ""       # the red glyph, "H" for a closed day
    weekend: bool = False
    closed: bool = False

    @property
    def filled(self) -> bool:
        return self.date is not None


def month_offset(year: int, month: int) -> int:
    """How many columns the row of `month` is pushed to the right."""
    return dt.date(year, month, 1).weekday()


def build(year: int, entries_by_date: dict[dt.date, object]) -> list[list[Cell]]:
    """A 12 x COLUMNS matrix of cells, one row per month."""
    rows = [
        [Cell(weekend=(c % 7) >= 5) for c in range(COLUMNS)]
        for _ in range(12)
    ]

    for month in range(1, 13):
        offset = month_offset(year, month)
        days = calendar.monthrange(year, month)[1]
        for day in range(1, days + 1):
            date = dt.date(year, month, day)
            cell = rows[month - 1][offset + day - 1]
            cell.date = date
            cell.weekend = date.weekday() >= 5
            entry = entries_by_date.get(date)
            if entry is not None:
                cell.label = entry.label
                cell.qualifier = entry.qualifier
                cell.closed = entry.closed
                cell.marker = "H" if entry.closed else ""

    return rows


def weekday_row() -> list[str]:
    """The Mon..Sun strip printed along the top and bottom of the sheet."""
    return [WEEKDAY_NAMES[c % 7] for c in range(COLUMNS)]
