---
layout: default
title: "Trace and loading"
---

# Trace and loading


## Structured Trace

```python
from app.services.execution_trace import Trace

Trace.info("job", "Execution started")
Trace.success("sql", "Data saved")
Trace.warning("excel", "Some rows were skipped")
Trace.error("ml", "Training failed")
Trace.record("dispatcher", "Handler selected", status="info")
```

Allowed sections: job, scheme, pilot, process, dispatcher, sql, excel, ml. Allowed statuses: info, success, warning, error. Invalid values raise ValueError. Extend the enums explicitly before using a new section.

| Status | Display |
|---|---|
| info | Blue information icon |
| success | Green check |
| warning | Amber warning |
| error | Red error icon |

Trace.warning/error records a message; it does not fail a job. Raise an exception when execution should fail. The runtime adds job start and completion/error messages. Compatibility Log.info/warning/error maps to process.

TraceEntry contains a sequence ID, UTC timestamp, section, status and message. The runtime retains the latest 400 entries in memory. Logs disappear on server restart; this is not persistent audit history.

The Log UI filters section and status independently. Filters survive view switches via shell.memory; messages use textContent. Register Log in BottomMenu to display traces; see Menus.

Never record passwords, full credential payloads or secret-bearing exception messages. Runtime exception handling logs str(exc), so keep exception text safe.

## Global loading

```python
from app.services.progress_bar import ProgressBar

ProgressBar.start("Processing data…")
try:
    result = perform_operation()
finally:
    ProgressBar.end()
```

perform_operation is your real function, not a framework API. No update method or percentage exists. Start/end are not reference-counted; one operation should own the overlay.

The browser makes the application inert during active loading. Server guards reject new POSTs while loading or a job is running. Ending the overlay does not cancel or finish the Python job. Runtime cleanup calls end as a safety net, but a permanently blocked task needs its own timeout strategy.

A short action may complete between polls, so the overlay may not be visibly rendered. Do not add artificial delays to real operations only to show it.
