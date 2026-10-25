"""Execute a fresh kernel in the notebook folder, without changing UI cwd."""
import atexit
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

from ..notebook_jobs import NOTEBOOK_JOBS, CELL_TIMEOUT_SECONDS
from .workspace_context import services


class NotebookRunError(RuntimeError):
    pass


def run_notebook(action_id, *, interactive=False):
    if type(interactive) is not bool:
        raise TypeError("interactive must be a boolean")
    runtime = services()
    project = Path(__file__).resolve().parents[2]
    relative = NOTEBOOK_JOBS.get(action_id)
    if not relative:
        raise NotebookRunError("No notebook configured for this action. Check the log.")
    source = (project / relative).resolve()
    if not source.is_relative_to(project) or not source.is_file():
        runtime.log(f"Notebook not found: {relative}", "job", "error")
        raise NotebookRunError("Notebook file not found. Check the log.")

    try:
        import nbformat
        import ipykernel  # Verify that the selected interpreter can launch a kernel.
        from nbclient import NotebookClient
    except ImportError as exc:
        runtime.log("Install requirements-notebooks.txt in the UI Python environment.", "job", "error")
        raise NotebookRunError("Notebook execution dependencies are missing. Check the log.") from exc

    configuration = runtime.store.get("database.configuration", {})
    secret = configuration.get("password", "") if isinstance(configuration, dict) else ""

    def clean(text):
        text = str(text)
        if secret:
            text = text.replace(secret, "[REDACTED]")
        return re.sub(r'(?i)([\"\']?(?:password|passwd|pwd)[\"\']?\s*[:=]\s*)([\"\'])(.*?)\2',
                      r'\1"[REDACTED]"', text)

    nb = nbformat.reads(source.read_text(encoding="utf-8-sig"), as_version=4)
    # Remove saved error allowances/skip tags: every actual code cell must succeed.
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            cell.metadata["tags"] = []

    marker = "AI4SH_LOG_" + uuid4().hex + ":"
    # UI launches route log events over IOPub to this specific runtime. Independent
    # notebook execution retains the existing HTTP bridge. No manual bind is needed.
    bootstrap = f'''
interactive = {interactive!r}
import sys as _ai4sh_sys, json as _ai4sh_json
_ai4sh_sys.path.insert(0, {str(project)!r})
import app.services.workspace_context as _ai4sh_context
class _AI4SHNotebookLog:
    def log(self, message, section="process", status="info"):
        section = getattr(section, "value", section)
        status = getattr(status, "value", status)
        print({marker!r} + _ai4sh_json.dumps(dict(message=str(message), section=section, status=status)), flush=True)
    def __getattr__(self, name):
        raise RuntimeError("Only log() is available in a notebook kernel: " + name)
_ai4sh_log = _AI4SHNotebookLog()
_ai4sh_context.notebook_services = _ai4sh_log
'''
    nb.cells.insert(0, nbformat.v4.new_code_cell(bootstrap))
    pending = {}
    # Only Jupyter error messages (uncaught exceptions) mark a cell failed.
    # Log severity and printed ERROR text never control execution outcome.
    failed_cells = set()

    def emit_line(line, cell_index):
        if line.startswith(marker):
            event = json.loads(line[len(marker):])
            runtime.log(clean(event["message"]), event["section"], event["status"])
        elif line.strip():
            error_line = bool(re.match(r"^\s*(?:❌\s*)?(?:ERROR\b|FATAL\b)", line, re.I))
            runtime.log(clean(line), "process", "error" if error_line else "info")

    class StreamingClient(NotebookClient):
        def process_message(self, msg, cell, cell_index):
            output = super().process_message(msg, cell, cell_index)
            kind = msg.get("msg_type", msg.get("header", {}).get("msg_type"))
            content = msg.get("content", {})
            if kind == "stream":
                key = (cell_index, content.get("name", "stdout"))
                text = pending.get(key, "") + content.get("text", "")
                lines = text.split("\n")
                pending[key] = lines.pop()
                for line in lines:
                    emit_line(line, cell_index)
            elif kind == "error":
                runtime.log(clean(f"Cell {cell_index}: {content.get('ename')}: {content.get('evalue')}"), "job", "error")
                failed_cells.add(cell_index)
            return output

    def report(cell, cell_index, execute_reply=None):
        for key in list(pending):
            if key[0] == cell_index:
                emit_line(pending.pop(key), cell_index)
        if cell_index in failed_cells:
            raise NotebookRunError("Notebook execution failed. Check the log.")

    client = StreamingClient(nb, timeout=CELL_TIMEOUT_SECONDS, kernel_name="python3",
                             allow_errors=False, force_raise_errors=True,
                             on_cell_executed=report,
                             resources={"metadata": {"path": str(source.parent)}})
    # Use the UI interpreter, not an unrelated machine-wide python3 kernelspec.
    manager = client.create_kernel_manager()
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client.km = manager
    runtime.log(f"Running {relative}", "job", "info")
    try:
        client.execute(cwd=str(source.parent))
    except NotebookRunError:
        raise
    except Exception as exc:
        # CellExecutionError.__str__ embeds the full cell source; don't log that.
        runtime.log(clean(f"Notebook stopped: {type(exc).__name__}"), "job", "error")
        raise NotebookRunError("Notebook execution failed. Check the log.") from exc
    finally:
        # nbclient registers cleanup before startup; remove it even if startup fails.
        atexit.unregister(client._cleanup_kernel)
    return {"notebook": relative}
