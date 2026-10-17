# Structured trace facade. Enum conversion validates sections and statuses before runtime logging.
# Trace messages must never contain passwords or credential payloads.
from .workspace_context import services
from ..models.trace_entry import TraceSection, TraceStatus

class Trace:
    @staticmethod
    # Validate enum values and pass a string message to runtime trace storage.
    # Invalid sections or statuses raise ValueError instead of inventing new categories.
    def record(section, text, status="info"):
        services().log(str(text), TraceSection(section), TraceStatus(status))

    @staticmethod
    # Record informational status.
    def info(section, text): Trace.record(section, text, "info")

    @staticmethod
    # Record a successful step; this alone does not determine overall job success.
    def success(section, text): Trace.record(section, text, "success")

    @staticmethod
    # Record a warning without changing execution flow.
    def warning(section, text): Trace.record(section, text, "warning")

    @staticmethod
    # Record an error without raising; actual failure requires a separate exception.
    def error(section, text): Trace.record(section, text, "error")
