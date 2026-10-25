"""Shared setup for the AI4SH import notebooks.

Keep this file beside the notebooks, inside the original project tree.
"""
from pathlib import Path
import sys


def get_store():
    """Locate the project once and return its existing Store class."""
    project = next(
        (parent for parent in Path(__file__).resolve().parents
         if (parent / "app" / "services" / "persistent_store.py").is_file()),
        None,
    )
    if project is None:
        raise RuntimeError(
            "Cannot find app/services/persistent_store.py. "
            "Keep this helper beside the notebooks inside the AI4SH project."
        )
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from app.services.persistent_store import Store
    return Store
