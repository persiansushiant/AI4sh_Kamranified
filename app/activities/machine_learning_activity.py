# Placeholder for the machine-learning workspace page. No model training is implemented.
from .activity_base import Activity
from ..services.workspace_mode import get_mode


class MachineLearningActivity(Activity):
    # Register metadata for the machine_learning activity.
    def __init__(self):
        super().__init__("machine_learning")

    # Expose the overall workspace mode, not the separate import_data.mode.
    def load(self):
        return {"mode": get_mode()}

    # Reject execution until real ML behavior is implemented.
    def run(self, payload):
        raise ValueError("Machine learning has not been implemented yet.")
