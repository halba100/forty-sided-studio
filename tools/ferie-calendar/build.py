#!/usr/bin/env python3
"""Build the A3 holiday planner for a given year.

    python3 build.py 2028            # draft the year's data, then draw the sheet

The data file (data/<year>.toml) is written once and never overwritten: edit it
by hand to add the closures and granted days, then run the command again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from calferie import model, sheet

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("year", type=int, help="the year to print, e.g. 2028")
    parser.add_argument("--data", type=Path, default=ROOT / "data",
                        help="where the per-year data files live")
    parser.add_argument("--out", type=Path, default=ROOT / "out",
                        help="where the sheet is written")
    args = parser.parse_args(argv)

    if not 1900 <= args.year <= 2200:
        parser.error(f"{args.year} is not a year this planner covers")

    data_path = args.data / f"{args.year}.toml"
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

    pdf_path = args.out / f"holiday-planner-{args.year}.pdf"
    sheet.render(planner, pdf_path, ROOT)
    print(f"wrote {pdf_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
