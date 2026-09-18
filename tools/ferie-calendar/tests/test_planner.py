"""Checks that the sheet stays faithful to the printed poster, and portable."""

from __future__ import annotations

import ast
import datetime as dt
import re
import struct
import sys
import tempfile
import tokenize
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calferie import grid, images, model, pdf, sheet          # noqa: E402
from calferie.holidays import easter_sunday, statutory_entries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


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
        self.assertEqual(
            entries["Easter Monday"].date, easter_sunday(2028) + dt.timedelta(1)
        )


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
            path = Path(tmp) / "2029.toml"
            model.dump(planner, path)
            reloaded = model.load(path)
        self.assertEqual(
            [(e.date, e.label, e.kind) for e in planner.entries],
            [(e.date, e.label, e.kind) for e in reloaded.entries],
        )
        self.assertEqual(planner.header, reloaded.header)

    def test_a_quote_in_a_label_survives(self):
        planner = model.draft(2029)
        planner.entries[0].label = 'A "quoted" \\ day'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2029.toml"
            model.dump(planner, path)
            self.assertEqual(model.load(path).entries[0].label, 'A "quoted" \\ day')

    def _reject(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2029.toml"
            path.write_text(body, encoding="utf-8")
            with self.assertRaises(ValueError):
                model.load(path)

    def test_two_entries_on_one_day_are_refused(self):
        self._reject(
            'year = 2029\n[[holidays]]\ndate = 2029-01-01\nlabel = "One"\n'
            '[[holidays]]\ndate = 2029-01-01\nlabel = "Two"\n'
        )

    def test_an_unknown_kind_is_refused(self):
        self._reject(
            'year = 2029\n[[holidays]]\ndate = 2029-01-01\n'
            'label = "One"\nkind = "bank-holiday"\n'
        )

    def test_a_date_from_another_year_is_refused(self):
        self._reject('year = 2029\n[[holidays]]\ndate = 2030-01-01\nlabel = "One"\n')


class TestPdf(unittest.TestCase):
    def test_text_width_grows_with_the_string_and_the_size(self):
        wide = pdf.text_width("MMMM", "Helvetica", 10)
        narrow = pdf.text_width("iiii", "Helvetica", 10)
        self.assertGreater(wide, narrow)
        self.assertAlmostEqual(
            pdf.text_width("January", "Helvetica", 14),
            pdf.text_width("January", "Helvetica", 7) * 2,
            places=6,
        )

    def test_every_font_carries_the_printable_ascii_range(self):
        for font in pdf.FONTS:
            self.assertEqual(len(pdf._METRICS[font]), 95, font)

    def test_the_page_is_a3_landscape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.pdf"
            page = pdf.Page(420, 297)
            page.text(10, 10, "hello")
            pdf.write(page, path)
            raw = path.read_bytes()
        self.assertTrue(raw.startswith(b"%PDF-"))
        self.assertTrue(raw.rstrip().endswith(b"%%EOF"))
        box = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", raw)
        self.assertIsNotNone(box)
        width, height = (float(v) / 72 * 25.4 for v in box.groups())
        self.assertAlmostEqual(width, 420, places=1)
        self.assertAlmostEqual(height, 297, places=1)
        self.assertEqual(raw.count(b"/Type /Page\n"), 0)   # one page, no stray dict
        self.assertIn(b"/Count 1", raw)

    def test_the_cross_reference_offsets_are_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.pdf"
            pdf.write(pdf.Page(100, 100), path)
            raw = path.read_bytes()
        start = int(re.search(rb"startxref\n(\d+)", raw).group(1))
        self.assertEqual(raw[start:start + 4], b"xref")
        for number, offset in enumerate(re.findall(rb"^(\d{10}) 00000 n", raw[start:],
                                                   re.M), start=1):
            self.assertEqual(
                raw[int(offset):int(offset) + len(str(number)) + 7],
                b"%d 0 obj\n" % number,
            )

    def test_turned_text_uses_the_quarter_turn_matrix(self):
        page = pdf.Page(100, 100)
        page.text(10, 50, "up", rotate=90)
        self.assertIn(b"0 1 -1 0", page.content())

    def test_a_parenthesis_in_a_label_is_escaped(self):
        page = pdf.Page(100, 100)
        page.text(10, 10, "HC (for 6 May)")
        self.assertIn(rb"(HC \(for 6 May\)) Tj", page.content())

    def test_text_can_only_be_upright_or_turned(self):
        with self.assertRaises(ValueError):
            pdf.Page(100, 100).text(0, 0, "x", rotate=45)


def _png(colour_type: int, channels: int, width=4, height=3, palette=b"") -> bytes:
    rows = b""
    for y in range(height):
        rows += b"\x00" + bytes(
            (x * 20 + y * 5 + c * 7) % 256
            for x in range(width) for c in range(channels)
        )

    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body)))

    out = images.PNG_MAGIC + chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    )
    if palette:
        out += chunk(b"PLTE", palette)
    return out + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class TestImages(unittest.TestCase):
    def load(self, raw: bytes) -> images.Image:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logo.png"
            path.write_bytes(raw)
            return images.load(path)

    def test_grey_and_colour_are_handed_over_untouched(self):
        for colour_type, channels, space in ((0, 1, b"/DeviceGray"), (2, 3, b"/DeviceRGB")):
            picture = self.load(_png(colour_type, channels))
            self.assertEqual(picture.colour_space, space)
            self.assertIsNone(picture.alpha)
            self.assertIn(b"/Predictor 15", picture.decode_parms)

    def test_a_palette_becomes_an_indexed_colour_space(self):
        picture = self.load(_png(3, 1, palette=bytes(range(12))))
        self.assertIn(b"/Indexed /DeviceRGB 3", picture.colour_space)

    def test_transparency_is_lifted_into_a_mask(self):
        picture = self.load(_png(6, 4))
        self.assertEqual(picture.colour_space, b"/DeviceRGB")
        self.assertIsNotNone(picture.alpha)
        self.assertEqual(len(zlib.decompress(picture.alpha)), 4 * 3)
        self.assertEqual(len(zlib.decompress(picture.data)), 4 * 3 * 3)

    def test_the_refusals_say_what_to_do_instead(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logo.png"
            path.write_bytes(b"not an image at all")
            with self.assertRaises(images.UnsupportedImage) as caught:
                images.load(path)
        self.assertIn("PNG", str(caught.exception))
        self.assertIn("JPEG", str(caught.exception))

    def test_sixteen_bit_and_interlaced_are_refused(self):
        deep = bytearray(_png(2, 3))
        deep[24] = 16                     # the bit depth, inside IHDR
        interlaced = bytearray(_png(2, 3))
        interlaced[28] = 1                # the interlace flag
        for raw in (deep, interlaced):
            with self.assertRaises(images.UnsupportedImage):
                self.load(bytes(raw))


class TestPortability(unittest.TestCase):
    """The sheet is drawn on a Windows laptop as often as anywhere else."""

    def sources(self):
        return sorted(ROOT.glob("calferie/*.py")) + [ROOT / "build.py"]

    def test_nothing_outside_the_standard_library_is_imported(self):
        allowed = {
            "__future__", "argparse", "ast", "calendar", "dataclasses",
            "datetime", "pathlib", "re", "struct", "sys", "tomllib", "zlib",
        }
        for source in self.sources():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [] if node.level else [node.module.split(".")[0]]
                else:
                    continue
                for name in names:
                    self.assertIn(name, allowed | {"calferie"}, source.name)

    def test_no_glibc_only_date_directives(self):
        # "%-d" and its kin are a glibc extension: strftime on Windows raises
        # ValueError on them. Comments are dropped so they can name the trap.
        pattern = re.compile(r"%[-#]\w")
        for source in self.sources():
            with tokenize.open(source) as handle:
                code = "".join(
                    token.string
                    for token in tokenize.generate_tokens(handle.readline)
                    if token.type != tokenize.COMMENT
                )
            self.assertEqual(pattern.findall(code), [], source.name)

    def test_the_reminders_read_correctly(self):
        planner = model.draft(2027)          # 25 December 2027 is a Saturday
        self.assertIn(
            "25 Dec (Saturday) Christmas: falls on a weekend, "
            "a day in lieu has to be chosen",
            model.todo(planner),
        )

    def test_every_file_is_read_and_written_as_utf8(self):
        # Windows defaults to the ANSI code page, which mangles the labels.
        for source in self.sources():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                keywords = {kw.arg for kw in node.keywords}
                where = f"{source.name} line {node.lineno}"
                if getattr(node.func, "attr", None) in ("read_text", "write_text"):
                    self.assertIn("encoding", keywords, where)
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    mode = next(
                        (a.value for a in node.args[1:2] if isinstance(a, ast.Constant)),
                        "r",
                    )
                    if "b" not in mode:
                        self.assertIn("encoding", keywords, where)


@unittest.skipUnless((DATA / "2027.toml").exists(), "the 2027 sheet is not in this checkout")
class TestTheTwentyTwentySevenSheet(unittest.TestCase):
    """2027 is the reference the generator was built against.

    The days come from the printed CMRE poster, plus the patron saint's day
    on 19 March, which the centre added afterwards.
    """

    CLOSED_2027 = {
        (1, 1), (1, 4), (1, 5), (1, 6),
        (3, 19), (3, 26), (3, 29),
        (6, 2),
        (8, 16),
        (11, 1),
        (12, 8), (12, 23), (12, 24), (12, 27), (12, 28), (12, 29), (12, 30), (12, 31),
    }

    def planner(self):
        return model.load(DATA / "2027.toml")

    def test_the_closed_days_match(self):
        closed = {(e.date.month, e.date.day) for e in self.planner().entries if e.closed}
        self.assertEqual(closed, self.CLOSED_2027)

    def test_labelled_working_days_carry_no_marker(self):
        by_date = self.planner().by_date()
        for month, day in ((4, 25), (5, 1), (12, 25), (12, 26)):
            self.assertFalse(by_date[dt.date(2027, month, day)].closed)

    def test_the_sheet_carries_every_label(self):
        page = sheet.draw(self.planner(), ROOT)
        content = page.content()
        # Round brackets are escaped inside a PDF string literal.
        for text in (b"Immaculate Conception", rb"\(in lieu of 15 Aug\)",
                     b"Director's Grant", b"2027", b"January", b"December"):
            self.assertIn(text, content, text)

    def test_the_sheet_draws_a_cell_for_every_day(self):
        page = sheet.draw(self.planner(), ROOT)
        # A rectangle both filled and stroked is a day cell, or the logo card;
        # the page, the year box and the bands are filled only, the frame is
        # stroked only.
        self.assertEqual(page.content().count(b" re\nB"), 365 + 1)


if __name__ == "__main__":
    unittest.main()
