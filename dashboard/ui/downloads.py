from __future__ import annotations

import pandas as pd

from dashboard.ui.components import st
from swing_rsi.application.dashboard_exports import to_csv_bytes, to_xlsx_bytes


def render_table_downloads(frame: pd.DataFrame, *, basename: str, label: str = "table") -> None:
    streamlit = st()
    columns = streamlit.columns(2)
    columns[0].download_button(
        f"Download {label} CSV",
        data=to_csv_bytes(frame),
        file_name=f"{basename}.csv",
        mime="text/csv",
        disabled=frame.empty,
    )
    columns[1].download_button(
        f"Download {label} XLSX",
        data=to_xlsx_bytes(frame, sheet_name=label[:31] or "data"),
        file_name=f"{basename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=frame.empty,
    )
