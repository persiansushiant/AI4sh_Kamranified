# Compatibility logging facade. All messages are mapped to the process Trace section.
from .execution_trace import Trace

class Log:
    @staticmethod
    # Record a compatibility info message in the process section.
    def info(text): Trace.info("process", text)
    @staticmethod
    # Record a warning; this does not fail or cancel the running job.
    def warning(text): Trace.warning("process", text)
    @staticmethod
    # Record an error message; callers must raise separately when execution should fail.
    def error(text): Trace.error("process", text)
