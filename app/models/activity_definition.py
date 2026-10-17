# Activity metadata exchanged with the shell. This dataclass is not an ORM table.
from dataclasses import dataclass, asdict

@dataclass
class ActivityDefinition:
    # The activity string ID links Python behavior to its matching HTML and JavaScript files.
    id: str
    title: str = ""
    icon: str = ""
    enabled: bool = True
    # The shell can display this explanation when a menu entry is disabled.
    reason: str = ""
    # Default placement is the main workspace; bottom registration overrides it.
    placement: str = "main"

    # Return a plain dictionary for shell state serialization.
    def to_dict(self):
        return asdict(self)
