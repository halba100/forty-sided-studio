"""Drawing the planner onto an A3 sheet.

Every measurement is in millimetres, taken from the top left corner of the
page, and gathered at the top of this module: the sheet is retuned by changing
the numbers here, not the code below them.
"""

from __future__ import annotations

from pathlib import Path

from . import grid, images, pdf
from .model import Planner

# Sheet -----------------------------------------------------------------
PAGE_W, PAGE_H = 420, 297       # A3 landscape
MARGIN = 6
HEADER_H = 28
SIDE_W = 26                     # the strip holding the URL and the year
GAP = 2
MONTH_W = 8                     # the month name bands, left and right
WEEKDAY_H = 5.5                 # the Mon..Sun bands, top and bottom

# Ink -------------------------------------------------------------------
DEFAULT_PAPER = "#8e9aab"       # "#ffffff" to print on a white sheet
BAND = "#1f3f73"
BAND_INK = "#ffffff"
CELL = "#f4f5f3"
WEEKEND = "#cbe0d7"
HOLIDAY = "#c00000"
RULE = "#7f97b8"
INK = "#1b2a4a"

# Type, in points ------------------------------------------------------
DAY_SIZE = 9.5
LABEL_SIZE = 5                  # the size a label is drawn at when it fits
LABEL_MIN_SIZE = 3.2            # how far a long one may be shrunk to fit
LABEL_LEAD = 2.3                # across the cell, from a label to its qualifier
WEEKDAY_SIZE = 6.5
MONTH_SIZE = 7
ORG_SIZE = 20
CENTRE_SIZE = 18
URL_SIZE = 15
YEAR_SIZE = 28
FOOTNOTE_SIZE = 6
FOOTNOTE_LEAD = 2.8             # from one footnote to the next

PLAIN = "Helvetica"
BOLD = "Helvetica-Bold"
ITALIC = "Helvetica-Oblique"
TITLE = "Times-Italic"


def _luminance(colour: str) -> float:
    """Rough perceived brightness of a #rrggbb colour, 0 (black) to 1 (white)."""
    value = colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


LOGO_W, LOGO_H = 34, 24


def _draw_logo(page: pdf.Page, planner: Planner, root: Path) -> None:
    """The logo at the top left, or an empty box saying one is wanted.

    A logo is drawn on its own: no card, no border and no padding around it,
    since the artwork carries whatever frame it wants.
    """
    name = str(planner.header.get("logo", ""))
    path = Path(name)
    if not path.is_absolute():
        path = root / path

    picture = None
    if name and path.exists():
        try:
            picture = images.load(path)
        except images.UnsupportedImage as problem:
            print(f"  note: {problem}")
    elif name:
        print(f"  note: {name} is missing, the logo box stays empty")

    if picture is not None:
        page.fit(MARGIN, MARGIN, LOGO_W, LOGO_H, picture)
        return

    page.rect(MARGIN, MARGIN, LOGO_W, LOGO_H, fill="#ffffff", stroke=BAND,
              line_width=0.3)
    page.text(MARGIN + LOGO_W / 2, MARGIN + 11, "LOGO", PLAIN, 9, RULE,
              align="centre")
    page.text(MARGIN + LOGO_W / 2, MARGIN + 16,
              "set header.logo to a PNG or JPEG", PLAIN, 4.5, BAND, align="centre")


def _draw_header(page: pdf.Page, planner: Planner, title_ink: str, emboss: bool,
                 root: Path) -> None:
    _draw_logo(page, planner, root)

    middle = PAGE_W / 2
    for text, size, baseline in (
        (planner.header["organization"], ORG_SIZE, MARGIN + 10),
        (planner.header["centre"], CENTRE_SIZE, MARGIN + 19),
    ):
        if emboss:
            page.text(middle + 0.25, baseline + 0.25, text, TITLE, size,
                      "#000000", align="centre")
        page.text(middle, baseline, text, TITLE, size, title_ink, align="centre")


def _draw_side(page: pdf.Page, planner: Planner, title_ink: str, emboss: bool) -> None:
    """The URL running up the left edge, and the year at its foot."""
    url = planner.header["url"]
    baseline = MARGIN + SIDE_W - 5
    bottom = PAGE_H - MARGIN - 22
    middle = (HEADER_H + bottom) / 2 + pdf.text_width(url, BOLD, URL_SIZE) / 2
    if emboss:
        page.text(baseline + 0.25, middle + 0.25, url, BOLD, URL_SIZE,
                  "#000000", rotate=90)
    page.text(baseline, middle, url, BOLD, URL_SIZE, title_ink, rotate=90)

    year = str(planner.year)
    width = pdf.text_width(year, BOLD, YEAR_SIZE) + 4
    height = YEAR_SIZE / pdf.PT_PER_MM + 3
    page.rect(MARGIN, PAGE_H - MARGIN - height, width, height, fill="#ffffff")
    page.text(MARGIN + 2, PAGE_H - MARGIN - 2.8, year, BOLD, YEAR_SIZE, HOLIDAY)


def _footer_height(planner: Planner) -> float:
    """The room the footnotes need under the grid, if there are any."""
    if not planner.footnotes:
        return 0
    return len(planner.footnotes) * FOOTNOTE_LEAD + 1.5


def _draw_bands(page: pdf.Page, cells_left: float, cells_top: float,
                column_w: float, row_h: float, grid_bottom: float) -> None:
    """The weekday strips across the top and bottom, months down both sides."""
    grid_left = MARGIN + SIDE_W + GAP
    grid_right = PAGE_W - MARGIN
    grid_top = MARGIN + HEADER_H

    for top in (grid_top, grid_bottom - WEEKDAY_H):
        page.rect(grid_left, top, grid_right - grid_left, WEEKDAY_H, fill=BAND)
        for column, name in enumerate(grid.weekday_row()):
            page.text(
                cells_left + (column + 0.5) * column_w,
                top + WEEKDAY_H - 1.7,
                name, PLAIN, WEEKDAY_SIZE, BAND_INK, align="centre",
            )

    band_top = grid_top + WEEKDAY_H
    band_height = grid_bottom - WEEKDAY_H - band_top
    for left in (grid_left, grid_right - MONTH_W):
        page.rect(left, band_top, MONTH_W, band_height, fill=BAND)
        for month, name in enumerate(grid.MONTH_NAMES):
            page.text(
                left + MONTH_W / 2 + 1.2,
                cells_top + (month + 0.5) * row_h,
                name, PLAIN, MONTH_SIZE, BAND_INK, align="centre", rotate=90,
            )


LABEL_SQUEEZE = 0.85            # below this much of LABEL_SIZE, split instead


def _label_size(text: str, room: float) -> float:
    """LABEL_SIZE, or as much of it as `room` millimetres will take."""
    width = pdf.text_width(text, ITALIC, LABEL_SIZE)
    if width <= room:
        return LABEL_SIZE
    return max(LABEL_MIN_SIZE, LABEL_SIZE * room / width)


def _split(text: str, room: float) -> list[str]:
    """`text` in two, at the word break that leaves the longer half shortest."""
    words = text.split()
    best = None
    for at in range(1, len(words)):
        halves = [" ".join(words[:at]), " ".join(words[at:])]
        longest = max(pdf.text_width(half, ITALIC, LABEL_SIZE) for half in halves)
        if longest <= room and (best is None or longest < best[0]):
            best = (longest, halves)
    return best[1] if best else [text]


def _label_lines(text: str, room: float) -> list[str]:
    """A label as one line, or as two when squeezing it would cost too much.

    A label a hair too long is simply set a little smaller, which nobody
    notices; one that would have to shrink a lot reads better broken in two,
    the way the printed poster sets its longest names.
    """
    if _label_size(text, room) >= LABEL_SIZE * LABEL_SQUEEZE:
        return [text]
    return _split(text, room)


def _draw_cells(page: pdf.Page, planner: Planner, cells_left: float,
                cells_top: float, column_w: float, row_h: float) -> None:
    rows = grid.build(planner.year, planner.by_date())
    for month, row in enumerate(rows):
        top = cells_top + month * row_h
        for column, cell in enumerate(row):
            if not cell.filled:
                continue
            left = cells_left + column * column_w
            page.rect(
                left, top, column_w, row_h,
                fill=WEEKEND if cell.weekend else CELL,
                stroke=RULE,
            )

            day = str(cell.date.day)
            font = BOLD if cell.closed else PLAIN
            number_foot = top + DAY_SIZE / pdf.PT_PER_MM + 1
            page.text(left + 0.8, number_foot, day, font, DAY_SIZE, INK)
            if cell.marker:
                page.text(
                    left + 1.2 + pdf.text_width(day, font, DAY_SIZE),
                    number_foot, cell.marker, BOLD, DAY_SIZE, HOLIDAY,
                )

            # The label reads upwards, under the day number. Turned text rises
            # to the left of its baseline, so each line sits further right.
            foot = top + row_h - 1
            room = foot - number_foot - 1
            lines = _label_lines(cell.label, room) if cell.label else []
            if cell.qualifier:
                lines.append(cell.qualifier)
            for line, text in enumerate(lines):
                page.text(
                    left + 2.2 + line * LABEL_LEAD, foot, text,
                    ITALIC, _label_size(text, room), INK, rotate=90,
                )


def draw(planner: Planner, root: Path = Path(".")) -> pdf.Page:
    """The whole sheet, ready to be written out."""
    paper = str(planner.header.get("background", DEFAULT_PAPER))
    dark_sheet = _luminance(paper) < 0.62
    title_ink = BAND_INK if dark_sheet else BAND

    page = pdf.Page(PAGE_W, PAGE_H)
    page.rect(0, 0, PAGE_W, PAGE_H, fill=paper)

    grid_left = MARGIN + SIDE_W + GAP
    grid_bottom = PAGE_H - MARGIN - _footer_height(planner)
    cells_left = grid_left + MONTH_W
    cells_top = MARGIN + HEADER_H + WEEKDAY_H
    column_w = (PAGE_W - MARGIN - grid_left - 2 * MONTH_W) / grid.COLUMNS
    row_h = (grid_bottom - cells_top - WEEKDAY_H) / 12

    _draw_header(page, planner, title_ink, dark_sheet, root)
    _draw_side(page, planner, title_ink, dark_sheet)
    _draw_cells(page, planner, cells_left, cells_top, column_w, row_h)
    _draw_bands(page, cells_left, cells_top, column_w, row_h, grid_bottom)

    page.rect(
        grid_left, MARGIN + HEADER_H,
        PAGE_W - MARGIN - grid_left, grid_bottom - MARGIN - HEADER_H,
        stroke=BAND, line_width=0.5,
    )

    for index, note in enumerate(planner.footnotes):
        page.text(grid_left, grid_bottom + (index + 1) * FOOTNOTE_LEAD,
                  note, PLAIN, FOOTNOTE_SIZE, INK)
    return page


def render(planner: Planner, path: Path, root: Path = Path(".")) -> None:
    pdf.write(draw(planner, root), path)
