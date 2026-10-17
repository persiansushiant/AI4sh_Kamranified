# Shared Python activity contract. Subclasses supply their own data and actions.
# Opening a view uses load(); background execution uses on_start(), run(), and on_end().
from ..models.activity_definition import ActivityDefinition
from ..services.activity_log import Log

# Menu registration expects activity subclasses to have constructors with no required arguments.
class Activity:
    # Keep metadata in ActivityDefinition rather than adding UI or database behavior here.
    def __init__(self, activity_id, title="", icon="", placement="main"):
        self.definition = ActivityDefinition(activity_id, title, icon, placement=placement)

    @property
    # The string ID links Python behavior to its UI template and browser module.
    def id(self): return self.definition.id

    @property
    # Expose the current availability stored in the metadata definition.
    def enabled(self): return self.definition.enabled

    @property
    # Resolve the template using the shared activity filename convention.
    def template(self): return f"activities/{self.id}_activity_ui.html"

    # Default lifecycle hook called before background execution; opening a page does not call it.
    def on_start(self): Log.info(f"{self.id}: on_start")

    # Default lifecycle cleanup hook; the runtime attempts it even after execution errors.
    def on_end(self): Log.info(f"{self.id}: on_end")

    # Default read-only UI data. Subclasses override this to restore existing state.
    def load(self): return {}

    # Activities without an action reject execution rather than reporting a false success.
    def run(self, payload): raise ValueError("This activity has no runnable action")

    # Serialize the definition for the workspace shell; do not expose live model objects.
    def metadata(self): return self.definition.to_dict()
