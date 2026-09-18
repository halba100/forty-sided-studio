"""Checks that the sheet stays faithful to the printed poster."""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calferie import grid, model, render                     # noqa: E402
from calferie.holidays import easter_sunday, statutory_entries  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


class TestEaster(unittest.TestCase):
    def test_known_years(self):
        expected = {
            2024: dt.date(2024, 3, 31),
            2025: dt.date(2025, 4, 20),
            2026: dt.date(2026, 4, 5),
            2027: dt.date(2027, 3, 28),
            2028: dt.date(2028, 4, 16),
            2030: dt.date(2030, 4, 21),
            2038: dt.date(2038, 4, 25),
        }
        for year, date in expected.items():
            self.assertEqual(easter_sunday(year), date, year)

    def test_always_a_sunday(self):
        for year in range(2020, 2101):
            self.assertEqual(easter_sunday(year).weekday(), 6, year)


class TestStatutory(unittest.TestCase):
    def test_a_weekend_holiday_loses_its_marker(self):
        # 25 December 2027 is a Saturday, so the centre is not closed on it.
        entries = {e.date: e for e in statutory_entries(2027)}
        self.assertEqual(entries[dt.date(2027, 12, 25)].kind, "note")
        self.assertFalse(entries[dt.date(2027, 12, 25)].closed)
        # 8 December 2027 is a Wednesday and stays a closed day.
        self.assertTrue(entries[dt.date(2027, 12, 8)].closed)

    def test_easter_monday_follows_easter(self):
        entries = {e.label: e for e in statutory_entries(2028)}
        self.assertEqual(entries["Easter Monday"].date, easter_sunday(2028) + dt.timedelta(1))


class TestGrid(unittest.TestCase):
    def test_every_day_is_placed_once(self):
        for year in (2024, 2027, 2028, 2100):  # 2024 is a leap year, 2100 is not
            rows = grid.build(year, {})
            placed = [c.date for row in rows for c in row if c.filled]
            days = 366 if len(placed) == 366 else 365
            self.assertEqual(len(placed), len(set(placed)), year)
            self.assertEqual(len(placed), days, year)

    def test_a_column_always_holds_one_weekday(self):
        for year in (2025, 2027, 2032):
            for row in grid.build(year, {}):
                for column, cell in enumerate(row):
                    if cell.filled:
                        self.assertEqual(cell.date.weekday(), column % 7)

    def test_the_grid_is_wide_enough(self):
        # A 31-day month starting on a Sunday is the widest case there is.
        self.assertEqual(grid.COLUMNS, 6 + 31)


class TestDataFile(unittest.TestCase):
    def test_round_trip(self):
        planner = model.draft(2029)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2029.yaml"
            model.dump(planner, path)
            reloaded = model.load(path)
        self.assertEqual(
            [(e.date, e.label, e.kind) for e in planner.entries],
            [(e.date, e.label, e.kind) for e in reloaded.entries],
        )

    def test_two_entries_on_one_day_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2029.yaml"
            path.write_text(
                "year: 2029\nholidays:\n"
                "  - date: 2029-01-01\n    label: One\n"
                "  - date: 2029-01-01\n    label: Two\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                model.load(path)

    def test_an_unknown_kind_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2029.yaml"
            path.write_text(
                "year: 2029\nholidays:\n  - date: 2029-01-01\n"
                "    label: One\n    kind: bank-holiday\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                model.load(path)


@unittest.skipUnless((DATA / "2027.yaml").exists(), "the 2027 sheet is not in this checkout")
class TestAgainstThePrintedPoster(unittest.TestCase):
    """The 2027 poster is the reference the generator was built against."""

    CLOSED_2027 = {
        (1, 1), (1, 4), (1, 5), (1, 6),
        (3, 26), (3, 29),
        (6, 2),
        (8, 16),
        (11, 1),
        (12, 8), (12, 23), (12, 24), (12, 27), (12, 28), (12, 29), (12, 30), (12, 31),
    }

    def test_the_closed_days_match(self):
        planner = model.load(DATA / "2027.yaml")
        closed = {(e.date.month, e.date.day) for e in planner.entries if e.closed}
        self.assertEqual(closed, self.CLOSED_2027)

    def test_labelled_working_days_carry_no_marker(self):
        planner = model.load(DATA / "2027.yaml")
        by_date = planner.by_date()
        for month, day in ((4, 25), (5, 1), (12, 25), (12, 26)):
            entry = by_date[dt.date(2027, month, day)]
            self.assertFalse(entry.closed, entry.label)

    def test_the_sheet_renders(self):
        html = render.render_html(model.load(DATA / "2027.yaml"))
        self.assertIn("Immaculate Conception", html)
        self.assertIn("(in lieu of 15 Aug)", html)
        self.assertEqual(html.count('class="weekday"'), 2 * grid.COLUMNS)


if __name__ == "__main__":
    unittest.main()
