# Startup registration entry point called with an active workspace service context.
# Current sidebar selection is delegated to the persisted workspace-mode service.
from .services.main_menu import MainMenu
from .services.bottom_menu import BottomMenu
from .services.persistent_store import Store
from .activities.log_activity import LogActivity
from .activities.configuration_summary_activity import ConfigurationSummaryActivity
from .services.workspace_mode import register_mode_activities
from .services.import_data_controls import set_import_data_mode

# Rebuild staged sidebar entries from persisted workspace mode.
# Unused imports are intentionally retained because this is a comment-only pass.
def configure():
    # This is your application's menu. No JavaScript changes are needed.

    register_mode_activities()