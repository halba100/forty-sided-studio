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
SIDE_W = 20                     # the strip holding the URL and the year
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

# Type ------------------------------------------------------------------
DAY_SIZE = 7.5
LABEL_SIZE = 3.8
WEEKDAY_SIZE = 6.5
MONTH_SIZE = 7
ORG_SIZE = 20
CENTRE_SIZE = 18
URL_SIZE = 15
YEAR_SIZE = 22

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
    """The logo card at the top left, or a box saying one is wanted."""
    page.rect(MARGIN, MARGIN, LOGO_W, LOGO_H, fill="#ffffff", stroke=BAND,
              line_width=0.3)

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
        page.fit(MARGIN + 1.5, MARGIN + 1.5, LOGO_W - 3, LOGO_H - 3, picture)
        return

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
    page.rect(MARGIN, PAGE_H - MARGIN - 12, width, 12, fill="#ffffff")
    page.text(MARGIN + 2, PAGE_H - MARGIN - 3.5, year, BOLD, YEAR_SIZE, HOLIDAY)


def _draw_bands(page: pdf.Page, cells_left: float, cells_top: float,
                column_w: float, row_h: float) -> None:
    """The weekday strips across the top and bottom, months down both sides."""
    grid_left = MARGIN + SIDE_W + GAP
    grid_right = PAGE_W - MARGIN
    grid_top = MARGIN + HEADER_H
    grid_bottom = PAGE_H - MARGIN

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
            page.text(left + 0.8, top + 3.4, day, font, DAY_SIZE, INK)
            if cell.marker:
                page.text(
                    left + 1.2 + pdf.text_width(day, font, DAY_SIZE),
                    top + 3.4, cell.marker, BOLD, DAY_SIZE, HOLIDAY,
                )

            # The label reads upwards, under the day number. Turned text rises
            # to the left of its baseline, so each line sits further right.
            foot = top + row_h - 1
            for line, text in enumerate(filter(None, (cell.label, cell.qualifier))):
                page.text(
                    left + 2.2 + line * 1.8, foot, text,
                    ITALIC, LABEL_SIZE, INK, rotate=90,
                )


def draw(planner: Planner, root: Path = Path(".")) -> pdf.Page:
    """The whole sheet, ready to be written out."""
    paper = str(planner.header.get("background", DEFAULT_PAPER))
    dark_sheet = _luminance(paper) < 0.62
    title_ink = BAND_INK if dark_sheet else BAND

    page = pdf.Page(PAGE_W, PAGE_H)
    page.rect(0, 0, PAGE_W, PAGE_H, fill=paper)

    grid_left = MARGIN + SIDE_W + GAP
    cells_left = grid_left + MONTH_W
    cells_top = MARGIN + HEADER_H + WEEKDAY_H
    column_w = (PAGE_W - MARGIN - grid_left - 2 * MONTH_W) / grid.COLUMNS
    row_h = (PAGE_H - MARGIN - cells_top - WEEKDAY_H) / 12

    _draw_header(page, planner, title_ink, dark_sheet, root)
    _draw_side(page, planner, title_ink, dark_sheet)
    _draw_cells(page, planner, cells_left, cells_top, column_w, row_h)
    _draw_bands(page, cells_left, cells_top, column_w, row_h)

    page.rect(
        grid_left, MARGIN + HEADER_H,
        PAGE_W - MARGIN - grid_left, PAGE_H - 2 * MARGIN - HEADER_H,
        stroke=BAND, line_width=0.5,
    )

    if planner.footnotes:
        for index, note in enumerate(planner.footnotes):
            page.text(grid_left, PAGE_H - MARGIN + 3.5 + index * 2.5,
                      note, PLAIN, 6, INK)
    return page


def render(planner: Planner, path: Path, root: Path = Path(".")) -> None:
    pdf.write(draw(planner, root), path)
