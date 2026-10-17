# Notes activity metadata. Session-only note behavior belongs to the browser activity.
from .activity_base import Activity

class NotesActivity(Activity):
    # Define notes metadata; this Python activity does not persist notes or run a save action.
    def __init__(self):
        super().__init__("notes", "Dynamic activity", "✎")
