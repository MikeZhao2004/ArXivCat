"""Entry point – choose UI backend via --ui flag or UI env var."""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="ArxivCat")
    parser.add_argument(
        "--ui",
        choices=["flet", "tk", "qt"],
        default="flet",
        help="UI backend to use (default: flet)",
    )
    args, _ = parser.parse_known_args()

    if args.ui == "tk":
        from arxivcat.ui.tkinter_ui import TkApp
        app = TkApp()
    elif args.ui == "qt":
        from arxivcat.ui.qt_ui import QtApp
        app = QtApp()
    else:
        from arxivcat.ui.flet_ui import FletApp
        app = FletApp()

    app.run()


if __name__ == "__main__":
    main()
