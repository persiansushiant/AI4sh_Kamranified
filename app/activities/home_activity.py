# Overview activity metadata. Its content is provided by the matching UI template.
from .activity_base import Activity

class HomeActivity(Activity):
    # Define the overview ID, title, and icon; inherited load() returns an empty object.
    def __init__(self):
        super().__init__("home", "Overview", "◈")
