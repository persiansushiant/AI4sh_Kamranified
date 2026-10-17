# Bottom-panel log activity. This file supplies filter choices from the Trace enums;
# trace storage and rendering belong to the runtime and browser UI.
from .activity_base import Activity

class LogActivity(Activity):
    # Place the log in the bottom panel rather than the main workspace.
    def __init__(self):
        super().__init__("log", "Log", "≡", placement="bottom")

    # Derive filter choices from the authoritative enums instead of duplicating allowed values.
    def load(self):
        from ..models.trace_entry import TraceSection, TraceStatus
        return {"sections": [section.value for section in TraceSection],
                "statuses": [status.value for status in TraceStatus]}
