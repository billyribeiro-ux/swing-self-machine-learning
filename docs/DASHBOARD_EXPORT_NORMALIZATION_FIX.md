# Dashboard Export Normalization Fix

## Root Cause

The shared dashboard export helper cleaned individual cell values but did not
normalize each output column's dtype afterward. A generic diagnostic table with
columns such as `Metric` and `Value` could keep `Value` as a mixed pandas
`object` column containing strings, `numpy.int64`, floats, booleans, missing
values, and infinities.

CSV and XLSX tolerated that mixture, but Streamlit/Arrow and Parquet conversion
could infer a bytes/string column and then fail when a later value was still a
numeric object:

```text
pyarrow.lib.ArrowTypeError:
("Expected bytes, got a 'numpy.int64' object",
 "Conversion failed for column Value with type object")
```

## Exact Failing Column/Table

The failing shape is a dashboard/report diagnostic table with a mixed display
column named `Value`. The same risk applies to other mixed display columns such
as `Actual`, `Threshold`, `Reason`, and `Status` when they contain both
human-readable strings and numeric or boolean Python objects.

The vulnerable path was the shared helper:

```text
src/swing_rsi/application/dashboard_exports.py
```

All dashboard CSV/XLSX download buttons and generated workbooks use that helper.

## Helper Added

Added:

```text
normalize_table_for_export(...)
```

Behavior:

- preserves numeric columns as numeric when all non-missing values are numeric;
- preserves date/datetime columns when all non-missing values are date-like;
- converts mixed display/object columns to redacted strings;
- keeps missing mixed-display values as `Not available`;
- keeps infinities distinguishable as `∞` and `-∞`;
- does not turn missing values into zero;
- redacts API-key-like content and secret marker text before export.

`to_csv_bytes(...)`, `to_xlsx_bytes(...)`, and `save_xlsx_report(...)` now use
the normalization path before serialization. XLSX row writing also converts
pandas nullable sentinels into blank worksheet cells.

## Files Changed

- `src/swing_rsi/application/dashboard_exports.py`
- `tests/test_streamlit_command_center.py`
- `docs/STREAMLIT_COMMAND_CENTER_DASHBOARD.md`
- `docs/SIGNAL_FIRST_DASHBOARD.md`
- `docs/CHANGELOG.md`
- `docs/DASHBOARD_EXPORT_NORMALIZATION_FIX.md`

## Tests Added

- Mixed `Value` column export with string, int, float, bool, `None`, `NaN`,
  `inf`, and `-inf`.
- CSV export success with redaction.
- XLSX export success and `openpyxl` load validation.
- Parquet/Arrow round trip from the normalized mixed table.
- Numeric-only table preservation.
- No misleading zero replacement for unavailable mixed-display values.
- No `.env` or API-key-looking content in export payloads.

## Verification Results

Focused dashboard/export verification:

```bash
.venv/bin/pytest tests/test_streamlit_command_center.py -q
```

Result:

```text
19 passed
```

Full verification:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

Results:

```text
327 passed
All checks passed!
118 files already formatted
Success: no issues found in 61 source files
```

Focused export smoke:

```bash
.venv/bin/python -c "..."
```

Result:

```text
dashboard export smoke passed
```

Local Streamlit HTTP smoke:

```bash
.venv/bin/streamlit run dashboard/app.py --server.port 8502 --server.headless true
curl -I http://localhost:8502
```

Result:

```text
HTTP/1.1 200 OK
```

## Launch Command

```bash
cd /Users/billyribeiro/Trading-Projects/swing-rsi-self-learner-dev
.venv/bin/streamlit run dashboard/app.py
```

## Safety Confirmation

This fix is reporting/export-only. It does not retrain models, run discovery,
update FMP data, run scanner, run forward update, run daily cycle, run
final-holdout update, promote models, change thresholds, change gates, mutate
SQLite on page load, mutate model artifacts, or modify the operational
repository.
