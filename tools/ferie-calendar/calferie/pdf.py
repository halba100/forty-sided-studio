"""A small PDF writer: rectangles, lines and text, measured in millimetres.

Only what the planner needs, and nothing outside the standard library. Pages
are addressed from the top left corner, the way a sheet of paper is read, and
the y axis is flipped on the way out to PDF's own bottom-left origin. Text
uses the fourteen fonts every PDF reader has built in, so no font file has to
be found, licensed or embedded.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .images import Image

PT_PER_MM = 72 / 25.4

# Character widths from Adobe's metrics for the built-in fonts, in thousandths
# of the point size, for the printable ASCII range (space through ~).
_WIDTHS = {
    "Helvetica": (
        "278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 "
        "556 556 556 556 556 556 556 556 556 556 278 278 584 584 584 556 "
        "1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 "
        "667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 "
        "333 556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 "
        "556 556 333 500 278 556 500 722 500 500 500 334 260 334 584"
    ),
    "Helvetica-Bold": (
        "278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 "
        "556 556 556 556 556 556 556 556 556 556 333 333 584 584 584 611 "
        "975 722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 "
        "667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 "
        "333 556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 "
        "611 611 389 556 333 611 556 778 556 556 500 389 280 389 584"
    ),
    "Times-Italic": (
        "250 333 420 500 500 833 778 214 333 333 500 675 250 333 250 278 "
        "500 500 500 500 500 500 500 500 500 500 333 333 675 675 675 500 "
        "920 611 611 667 722 611 611 722 722 333 444 667 556 833 667 722 "
        "611 722 611 500 556 722 611 833 611 556 556 389 278 389 422 500 "
        "333 500 500 444 500 444 278 500 500 278 278 444 278 722 500 500 "
        "500 500 389 389 278 500 444 667 444 444 389 400 275 400 541"
    ),
}
# The oblique cut of Helvetica is spaced exactly like the upright one.
_WIDTHS["Helvetica-Oblique"] = _WIDTHS["Helvetica"]

_METRICS = {
    name: [int(w) for w in widths.split()] for name, widths in _WIDTHS.items()
}
# What an unmapped character is assumed to cost.
_FALLBACK_WIDTH = 500

FONTS = tuple(_METRICS)


def _parse_colour(colour: str) -> tuple[float, float, float]:
    value = colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError(f"{colour!r} is not a #rrggbb colour")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def text_width(text: str, font: str, size: float, condense: float = 100) -> float:
    """How wide `text` prints, in millimetres.

    `condense` is the horizontal scaling as a percentage, the same number PDF
    itself takes: 100 leaves the face as drawn, 82 narrows it.
    """
    widths = _METRICS[font]
    total = 0
    for char in text:
        index = ord(char) - 32
        total += widths[index] if 0 <= index < len(widths) else _FALLBACK_WIDTH
    return total / 1000 * size * condense / 100 / PT_PER_MM


def _escape(text: str) -> bytes:
    """A PDF string literal, in the encoding the built-in fonts are shown in."""
    raw = text.encode("cp1252", errors="replace")
    for old, new in ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)")):
        raw = raw.replace(old, new)
    return raw


@dataclass
class Page:
    """One sheet, drawn from its top left corner in millimetres."""

    width: float
    height: float
    condense: float = 100        # horizontal scaling applied to text, per cent
    _parts: list[bytes] = field(default_factory=list)
    _images: list[Image] = field(default_factory=list)

    # -- geometry ------------------------------------------------------
    def _x(self, mm: float) -> float:
        return mm * PT_PER_MM

    def _y(self, mm: float) -> float:
        """Millimetres from the top become points from the bottom."""
        return (self.height - mm) * PT_PER_MM

    # -- drawing -------------------------------------------------------
    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str | None = None,
        stroke: str | None = None,
        line_width: float = 0.15,
    ) -> None:
        if fill is None and stroke is None:
            return
        parts = []
        if fill is not None:
            parts.append(b"%.4f %.4f %.4f rg" % _parse_colour(fill))
        if stroke is not None:
            parts.append(b"%.4f %.4f %.4f RG" % _parse_colour(stroke))
            parts.append(b"%.3f w" % (line_width * PT_PER_MM))
        parts.append(
            b"%.3f %.3f %.3f %.3f re"
            % (
                self._x(x),
                self._y(y + height),
                width * PT_PER_MM,
                height * PT_PER_MM,
            )
        )
        painter = {(True, True): b"B", (True, False): b"f", (False, True): b"S"}
        parts.append(painter[(fill is not None, stroke is not None)])
        self._parts.append(b"\n".join(parts))

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        colour: str = "#000000",
        width: float = 0.15,
    ) -> None:
        self._parts.append(
            b"\n".join(
                [
                    b"%.4f %.4f %.4f RG" % _parse_colour(colour),
                    b"%.3f w" % (width * PT_PER_MM),
                    b"%.3f %.3f m" % (self._x(x1), self._y(y1)),
                    b"%.3f %.3f l" % (self._x(x2), self._y(y2)),
                    b"S",
                ]
            )
        )

    def text(
        self,
        x: float,
        y: float,
        text: str,
        font: str = "Helvetica",
        size: float = 8,
        colour: str = "#000000",
        align: str = "left",
        rotate: int = 0,
        condense: float | None = None,
    ) -> None:
        """Draw `text` with its baseline at (x, y).

        `align` moves the string along its own direction of travel; `rotate`
        is 0 for upright text or 90 for text reading upwards; `condense`
        overrides the page's own horizontal scaling for this one string.
        """
        if not text:
            return
        if rotate not in (0, 90):
            raise ValueError("text can be drawn upright or turned 90 degrees")

        if condense is None:
            condense = self.condense
        length = text_width(text, font, size, condense)
        shift = {"left": 0.0, "centre": -length / 2, "right": -length}[align]
        if rotate == 0:
            x += shift
            matrix = b"1 0 0 1 %.3f %.3f Tm" % (self._x(x), self._y(y))
        else:
            y -= shift          # upwards is towards a smaller y from the top
            matrix = b"0 1 -1 0 %.3f %.3f Tm" % (self._x(x), self._y(y))

        self._parts.append(
            b"\n".join(
                [
                    b"%.4f %.4f %.4f rg" % _parse_colour(colour),
                    b"BT",
                    b"/%s %.2f Tf" % (font.replace("-", "").encode("ascii"), size),
                    b"%.2f Tz" % condense,
                    matrix,
                    b"(%s) Tj" % _escape(text),
                    b"ET",
                ]
            )
        )

    def image(self, x: float, y: float, width: float, height: float,
              picture: Image) -> None:
        """Place `picture` in the box (x, y, width, height)."""
        self._images.append(picture)
        self._parts.append(
            b"q\n%.3f 0 0 %.3f %.3f %.3f cm\n/Im%d Do\nQ"
            % (
                width * PT_PER_MM,
                height * PT_PER_MM,
                self._x(x),
                self._y(y + height),
                len(self._images) - 1,
            )
        )

    def fit(self, x: float, y: float, width: float, height: float,
            picture: Image) -> None:
        """Place `picture` inside the box, keeping its proportions, centred."""
        scale = min(width / picture.width, height / picture.height)
        drawn_w = picture.width * scale
        drawn_h = picture.height * scale
        self.image(
            x + (width - drawn_w) / 2, y + (height - drawn_h) / 2,
            drawn_w, drawn_h, picture,
        )

    def content(self) -> bytes:
        return b"\n".join(self._parts)


def write(page: Page, path: Path) -> None:
    """Save the page as a one-page PDF."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_ids = {}
    for font in FONTS:
        name = font.replace("-", "")
        font_ids[name] = add(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding "
            b"/WinAnsiEncoding >>" % font.encode("ascii")
        )

    xobjects = []
    for number, picture in enumerate(page._images):
        mask = b""
        if picture.alpha is not None:
            mask_id = add(
                b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                b"/ColorSpace /DeviceGray /BitsPerComponent 8 "
                b"/Filter /FlateDecode /Length %d >>\nstream\n%s\nendstream"
                % (picture.width, picture.height, len(picture.alpha), picture.alpha)
            )
            mask = b" /SMask %d 0 R" % mask_id
        parms = b" /DecodeParms " + picture.decode_parms if picture.decode_parms else b""
        image_id = add(
            b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            b"/ColorSpace %s /BitsPerComponent %d /Filter %s%s%s /Length %d >>"
            b"\nstream\n%s\nendstream"
            % (picture.width, picture.height, picture.colour_space, picture.bits,
               picture.filter, parms, mask, len(picture.data), picture.data)
        )
        xobjects.append(b"/Im%d %d 0 R" % (number, image_id))

    stream = zlib.compress(page.content(), 9)
    contents = add(
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream"
        % (len(stream), stream)
    )

    fonts = b" ".join(
        b"/%s %d 0 R" % (name.encode("ascii"), number)
        for name, number in font_ids.items()
    )
    resources = b"/Font << %s >>" % fonts
    if xobjects:
        resources += b" /XObject << %s >>" % b" ".join(xobjects)
    pages_id = len(objects) + 2          # the page comes first, then its parent
    page_id = add(
        b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
        b"/Resources << %s >> /Contents %d 0 R >>"
        % (pages_id, page.width * PT_PER_MM, page.height * PT_PER_MM,
           resources, contents)
    )
    add(b"<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % page_id)
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)

    start = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += (
        b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, catalog, start)
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
