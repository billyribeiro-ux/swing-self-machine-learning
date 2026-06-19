from __future__ import annotations

from dashboard.sections.overview import render_page
from dashboard.ui.components import configure_page


def main() -> None:
    configure_page("Swing RSI Dashboard")
    render_page()


if __name__ == "__main__":
    main()
