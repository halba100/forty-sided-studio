#!/usr/bin/env python3
"""Build the A3 holiday planner for a given year.

    python3 build.py 2028            # draft the year's data, then print it
    python3 build.py 2028 --png      # also write a preview image
    python3 build.py 2028 --html     # stop at the HTML, for tweaking the CSS

The data file (data/<year>.yaml) is written once and never overwritten: edit it
by hand to add the closures and granted days, then run the command again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from calferie import model, render

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("year", type=int, help="the year to print, e.g. 2028")
    parser.add_argument("--data", type=Path, default=ROOT / "data",
                        help="where the per-year YAML files live")
    parser.add_argument("--out", type=Path, default=ROOT / "out",
                        help="where the sheet is written")
    parser.add_argument("--html", action="store_true",
                        help="write the HTML only, skip the PDF")
    parser.add_argument("--png", action="store_true",
                        help="also write a PNG preview next to the PDF")
    args = parser.parse_args(argv)

    if not 1900 <= args.year <= 2200:
        parser.error(f"{args.year} is not a year this planner covers")

    data_path = args.data / f"{args.year}.yaml"
    if not data_path.exists():
        args.data.mkdir(parents=True, exist_ok=True)
        model.dump(model.draft(args.year), data_path)
        print(f"drafted {data_path} from the statutory holidays")

    planner = model.load(data_path)

    reminders = model.todo(planner)
    if reminders:
        print(f"still to decide for {args.year}:")
        for reminder in reminders:
            print(f"  - {reminder}")

    args.out.mkdir(parents=True, exist_ok=True)
    html_path = args.out / f"holiday-planner-{args.year}.html"
    html_path.write_text(render.render_html(planner, ROOT), encoding="utf-8")
    print(f"wrote {html_path}")

    if not args.html:
        pdf_path = args.out / f"holiday-planner-{args.year}.pdf"
        render.html_to_pdf(html_path, pdf_path)
        print(f"wrote {pdf_path}")

    if args.png:
        png_path = args.out / f"holiday-planner-{args.year}.png"
        render.html_to_png(html_path, png_path)
        print(f"wrote {png_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
