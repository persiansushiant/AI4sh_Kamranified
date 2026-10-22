# In-process single-workspace runtime with one active background job.
# Menus, commands, and the latest 400 trace entries are memory-only; Store is attached by the factory.
import threading
from collections import deque
from datetime import datetime, timezone
from uuid import uuid4
from .services.workspace_context import bind, unbind
from .services.log_bridge import LogBridge
from .services.progress_bar import ProgressBar
from .models.trace_entry import TraceEntry, TraceSection, TraceStatus

class Runtime:
    # Initialize bounded logs and commands, shared registry, menu mappings, and loading state.
    def __init__(self):
        self.lock = threading.RLock()
        self.logs = deque(maxlen=400)
        self.job = None
        self.sequence = 0
        self.registry = {}
        self.menu = {}
        self.bottom_menu = {}
        self.commands = deque(maxlen=100)
        self.command_sequence = 0
        self.progress_state = dict(active=False, text="")
        self.log_bridge = LogBridge(self)

    def close(self):
        """Stop the notebook log receiver when disposing of the runtime."""
        self.log_bridge.close()

    # Assign monotonically increasing command IDs so the browser can ignore already processed entries.
    def command(self, kind, value=None):
        with self.lock:
            self.command_sequence += 1
            self.commands.append(dict(id=self.command_sequence, kind=kind, value=value))

    # Create a validated immutable trace entry with a UTC timestamp and increasing sequence ID.
    def log(self, message, section="process", status="info"):
        with self.lock:
            self.sequence += 1
            self.logs.append(TraceEntry(self.sequence, datetime.now(timezone.utc).isoformat(timespec="milliseconds"), TraceSection(section), TraceStatus(status), str(message)))

    # Reject concurrent execution, record the running job, and start a daemon worker thread.
    def start(self, activity, payload):
        with self.lock:
            if self.job and self.job["status"] == "running":
                raise RuntimeError("Another activity is running")
            self.job = dict(id=str(uuid4()), activity=activity.id, status="running", result=None)
            job_id = self.job["id"]
        threading.Thread(target=self._execute, args=(activity, payload), daemon=True).start()
        return job_id

    # Bind services in the worker, run lifecycle hooks, and record success or failure.
    # Cleanup errors also fail the job; exception messages are logged, so callers must avoid secret-bearing errors.
    def _execute(self, activity, payload):
        token = bind(self)
        status, result = "succeeded", None
        try:
            self.log(f"Started {activity.id}", "job", "info")
            activity.on_start()
            result = activity.run(payload)
        except Exception as exc:
            status, result = "failed", {"message": str(exc)}
            self.log(f"ERROR: {exc}", "job", "error")
        finally:
            try:
                activity.on_end()
            except Exception as exc:
                status, result = "failed", {"message": str(exc)}
                self.log(f"ERROR in on_end: {exc}", "job", "error")
            # Safety net: even a forgotten end() or exception unlocks the app.
            ProgressBar.end()
            with self.lock:
                self.job.update(status=status, result=result)
            self.log(f"{activity.id}: {status}", "job", "success" if status == "succeeded" else "error")
            unbind(token)

    # Return serialized copies for polling, not live TraceEntry objects.
    def snapshot(self):
        with self.lock:
            return dict(job=dict(self.job) if self.job else None, logs=[entry.to_dict() for entry in self.logs],
                        progress=dict(self.progress_state), commands=list(self.commands))
