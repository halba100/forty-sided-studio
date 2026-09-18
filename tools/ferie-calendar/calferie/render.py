"""Turning a planner into an A3 sheet: Jinja2 for the HTML, Chromium for the PDF."""

from __future__ import annotations

import base64
import mimetypes
import ntpath
import os
import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import grid
from .model import Planner

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

# Any Chromium-based browser can print the sheet: Chromium, Chrome or Edge.
BROWSER_NAMES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "msedge",
)


def _windows_candidates() -> list[str]:
    """Where Edge and Chrome install themselves on Windows."""
    roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    relative = [
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
    ]
    # Joined with Windows rules whatever machine this runs on, so the paths
    # stay readable in an error message and testable from anywhere.
    return [ntpath.join(root, tail) for root in roots if root for tail in relative]


def _platform_candidates() -> list[str]:
    """The usual homes of a browser, once the PATH has come up empty."""
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/microsoft-edge",
        "/snap/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    candidates += _windows_candidates()
    # A browser downloaded by Playwright, as on a CI runner.
    candidates += [
        str(path)
        for path in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    ]
    return candidates


def find_chromium() -> str:
    """The browser used to print the sheet, or an error saying how to name one."""
    explicit = os.environ.get("CHROMIUM")
    if explicit:
        if Path(explicit).exists():
            return explicit
        on_path = shutil.which(explicit)
        if on_path:
            return on_path
        raise RuntimeError(f"$CHROMIUM points at {explicit}, which is not there")

    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found

    for candidate in _platform_candidates():
        if Path(candidate).exists():
            return candidate

    raise RuntimeError(
        "no Chromium-based browser found. Install Chrome, Chromium or Edge, "
        "or point $CHROMIUM at the one you have, for example:\n"
        r'  set CHROMIUM=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    )


def _data_uri(path: Path) -> str:
    """Images are inlined so the HTML file stands on its own."""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _luminance(colour: str) -> float:
    """Rough perceived brightness of a #rrggbb colour, 0 (black) to 1 (white)."""
    value = colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def render_html(planner: Planner, root: Path = ROOT) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        autoescape=True,
    )
    logos = []
    for key in ("logo_left", "logo_right"):
        value = planner.header.get(key)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        if path.exists():
            logos.append(_data_uri(path))
        else:
            print(f"  note: {value} is missing, the logo slot stays empty")

    paper = str(planner.header.get("background", "#8e9aab"))
    dark_sheet = _luminance(paper) < 0.62

    return env.get_template("planner.html.j2").render(
        planner=planner,
        rows=grid.build(planner.year, planner.by_date()),
        columns=grid.COLUMNS,
        months=grid.MONTH_NAMES,
        weekdays=grid.weekday_row(),
        logos=logos,
        paper=paper,
        title_ink="#ffffff" if dark_sheet else "#1f3f73",
        title_shadow="rgba(0, 0, 0, 0.35)" if dark_sheet else "transparent",
    )


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        find_chromium(),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(
            "Chromium could not print the sheet:\n" + (result.stderr or result.stdout)
        )


def html_to_png(html_path: Path, png_path: Path, width: int = 2480) -> None:
    """A preview image of the sheet, for checking it without a printer."""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    # The sheet is exactly A3 landscape, which is 1588 x 1123 CSS pixels at 96 dpi.
    css_w, css_h = 1588, 1123
    scale = round(width / css_w, 3)
    # Headless Chromium keeps back part of the window for browser furniture, so
    # ask for a taller one and trim the surplus off afterwards.
    window_h = css_h + 96
    command = [
        find_chromium(),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--window-size={css_w},{window_h}",
        f"--force-device-scale-factor={scale}",
        "--virtual-time-budget=4000",
        f"--screenshot={png_path}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not png_path.exists():
        raise RuntimeError(
            "Chromium could not take the preview:\n" + (result.stderr or result.stdout)
        )
    _trim(png_path, round(css_w * scale), round(css_h * scale))


def _trim(png_path: Path, width: int, height: int) -> None:
    """Cut the preview back to the size of the sheet, when Pillow is around."""
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(png_path) as image:
        if image.size != (width, height):
            image.crop((0, 0, width, height)).save(png_path)
