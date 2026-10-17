# Bottom-panel visibility and height commands. Selecting a bottom activity is a separate operation.
from .workspace_context import services

class BottomPanel:
    @staticmethod
    # Queue a command to reveal the panel.
    def open(): services().command("panel.open")
    @staticmethod
    # Queue a command to hide the panel without removing its activities.
    def close(): services().command("panel.close")
    @staticmethod
    # Coerce the requested height and enforce the server-side minimum of 90 pixels.
    # The browser applies its own viewport-dependent upper limit.
    def set_height(height): services().command("panel.height", max(90, int(height)))
