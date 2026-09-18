"""Reading a logo file into the pieces a PDF needs to show it.

PDF stores JPEG and Flate-compressed data natively, and it understands PNG's
own row filters, so most files can be handed over untouched. Only a PNG with
an alpha channel has to be unpacked here, to lift the transparency out into
the separate mask PDF wants.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass
class Image:
    width: int                      # in pixels
    height: int
    data: bytes                     # already in the encoding `filter` names
    colour_space: bytes             # a PDF name or array
    bits: int = 8
    filter: bytes = b"/FlateDecode"
    decode_parms: bytes = b""
    alpha: bytes | None = None      # greyscale mask, Flate compressed


class UnsupportedImage(Exception):
    """Raised with a sentence the person reading it can act on."""


def load(path: Path) -> Image:
    raw = path.read_bytes()
    if raw.startswith(PNG_MAGIC):
        return _load_png(raw, path)
    if raw.startswith(b"\xff\xd8"):
        return _load_jpeg(raw, path)
    raise UnsupportedImage(
        f"{path.name} is neither a PNG nor a JPEG; save the logo as one of those"
    )


# -- JPEG ---------------------------------------------------------------
_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _load_jpeg(raw: bytes, path: Path) -> Image:
    at = 2
    while at < len(raw) - 1:
        if raw[at] != 0xFF:
            at += 1
            continue
        marker = raw[at + 1]
        if marker in _SOF_MARKERS:
            height, width = struct.unpack(">HH", raw[at + 5:at + 9])
            components = raw[at + 9]
            spaces = {1: b"/DeviceGray", 3: b"/DeviceRGB", 4: b"/DeviceCMYK"}
            if components not in spaces:
                raise UnsupportedImage(
                    f"{path.name} has {components} colour channels, which is unusual; "
                    "save it again as a plain RGB JPEG"
                )
            return Image(
                width=width,
                height=height,
                data=raw,
                colour_space=spaces[components],
                filter=b"/DCTDecode",
            )
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            at += 2
            continue
        at += 2 + struct.unpack(">H", raw[at + 2:at + 4])[0]
    raise UnsupportedImage(f"{path.name} is a JPEG whose size I cannot read")


# -- PNG ----------------------------------------------------------------
def _chunks(raw: bytes):
    at = len(PNG_MAGIC)
    while at < len(raw):
        (length,) = struct.unpack(">I", raw[at:at + 4])
        kind = raw[at + 4:at + 8]
        yield kind, raw[at + 8:at + 8 + length]
        at += 12 + length           # length, kind, data, crc


def _load_png(raw: bytes, path: Path) -> Image:
    header = palette = transparency = None
    pixels = bytearray()
    for kind, body in _chunks(raw):
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = body
        elif kind == b"tRNS":
            transparency = body
        elif kind == b"IDAT":
            pixels += body
        elif kind == b"IEND":
            break

    if header is None:
        raise UnsupportedImage(f"{path.name} is a PNG without a header")
    width, height, bits, colour_type, _, _, interlace = header

    advice = "open it in any image editor and save it as a plain RGB PNG or a JPEG"
    if bits != 8:
        raise UnsupportedImage(f"{path.name} is {bits} bits per channel; {advice}")
    if interlace:
        raise UnsupportedImage(f"{path.name} is interlaced; {advice}")
    if colour_type == 3 and transparency is not None:
        raise UnsupportedImage(
            f"{path.name} has a transparent colour in its palette; {advice}"
        )

    common = dict(width=width, height=height, bits=8)

    # Greyscale, colour and palette rows are exactly what PDF expects, once it
    # is told to undo PNG's row filters itself.
    if colour_type in (0, 2, 3):
        channels = {0: 1, 2: 3, 3: 1}[colour_type]
        if colour_type == 3:
            if palette is None:
                raise UnsupportedImage(f"{path.name} is indexed but carries no palette")
            hival = len(palette) // 3 - 1
            space = b"[/Indexed /DeviceRGB %d <%s>]" % (hival, palette.hex().encode())
        else:
            space = b"/DeviceGray" if channels == 1 else b"/DeviceRGB"
        return Image(
            data=bytes(pixels),
            colour_space=space,
            decode_parms=(
                b"<< /Predictor 15 /Colors %d /BitsPerComponent 8 /Columns %d >>"
                % (channels, width)
            ),
            **common,
        )

    if colour_type not in (4, 6):
        raise UnsupportedImage(f"{path.name} has an unknown colour type; {advice}")

    # Grey+alpha and colour+alpha have to be taken apart: PDF keeps the
    # transparency in a mask of its own.
    channels = 2 if colour_type == 4 else 4
    rows = _unfilter(zlib.decompress(bytes(pixels)), width, height, channels)
    colour = bytearray()
    alpha = bytearray()
    for row in rows:
        for at in range(0, len(row), channels):
            colour += row[at:at + channels - 1]
            alpha.append(row[at + channels - 1])
    return Image(
        data=zlib.compress(bytes(colour), 9),
        colour_space=b"/DeviceGray" if channels == 2 else b"/DeviceRGB",
        alpha=zlib.compress(bytes(alpha), 9),
        **common,
    )


def _unfilter(raw: bytes, width: int, height: int, channels: int) -> list[bytearray]:
    """Undo the per-row filters PNG applies before compressing."""
    stride = width * channels
    previous = bytearray(stride)
    rows = []
    at = 0
    for _ in range(height):
        method = raw[at]
        row = bytearray(raw[at + 1:at + 1 + stride])
        at += 1 + stride
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            corner = previous[index - channels] if index >= channels else 0
            if method == 1:
                row[index] = (row[index] + left) & 0xFF
            elif method == 2:
                row[index] = (row[index] + up) & 0xFF
            elif method == 3:
                row[index] = (row[index] + (left + up) // 2) & 0xFF
            elif method == 4:
                row[index] = (row[index] + _paeth(left, up, corner)) & 0xFF
            elif method != 0:
                raise UnsupportedImage(f"unknown PNG row filter {method}")
        rows.append(row)
        previous = row
    return rows


def _paeth(left: int, up: int, corner: int) -> int:
    estimate = left + up - corner
    da, db, dc = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
    if da <= db and da <= dc:
        return left
    return up if db <= dc else corner
