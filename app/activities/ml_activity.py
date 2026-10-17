# Simulated training activity used to demonstrate loading, traces, and error cleanup.
# This demo is separate from MachineLearningActivity and does not train a model.
import time
from .activity_base import Activity
from ..services.progress_bar import ProgressBar
from ..services.execution_trace import Trace

class MlActivity(Activity):
    # Use the short ml ID for this demo; it differs from machine_learning.
    def __init__(self): super().__init__("ml")

    # Run ten simulated epochs and optionally demonstrate a controlled failure.
    def run(self, payload):
        ProgressBar.start("Training demo")
        try:
            # The delay simulates work. Trace entries are status messages, not percentage updates.
            for step in range(1, 11):
                time.sleep(.3)
                Trace.success("ml", f"Epoch {step} completed")
                # A truthy fail value intentionally raises during epoch four to exercise error handling.
                if payload.get("fail") and step == 4:
                    raise ValueError("Intentional demo failure")
            return {"message": "Demo experiment finished. No real ML was executed."}
        # Release loading on both the successful and intentionally failing paths.
        finally:
            ProgressBar.end()
