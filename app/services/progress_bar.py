# Shared loading overlay state. This API provides text and active state, not percentage progress.
from .workspace_context import services
from .bottom_menu import BottomMenu

class ProgressBar:
    @staticmethod
    # Set loading active with a string message under the runtime lock.
    # Start/end are not reference-counted; avoid overlapping ownership.
    def start(text="Working…", show_log=True):
        s = services()
        with s.lock:
            # Reveal Log once per inactive-to-active transition. Repeated text
            # updates must not take the user back to Log again.
            if show_log and not s.progress_state["active"]:
                # pop("log") registers and enables the built-in activity if needed.
                BottomMenu.pop("log")
            s.progress_state = dict(active=True, text=str(text))

    @staticmethod
    # Clear loading state. This does not cancel the running job or complete its lifecycle.
    def end():
        s = services()
        with s.lock:
            s.progress_state["active"] = False
