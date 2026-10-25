"""The existing encrypted Store, available in UI and independent notebooks."""
import os
from pathlib import Path
import threading
from .workspace_context import services


class Store:
    _lock = threading.RLock()
    _repositories = {}

    @staticmethod
    def configure(database_path):
        """Optional: select an existing workspace DB; child kernels inherit it."""
        os.environ["AI4SH_WORKSPACE_DATABASE"] = str(Path(database_path).resolve())

    @staticmethod
    def _repository():
        # The runtime remains authoritative when a UI context is bound.
        bound = vars(services()).get("store")
        if bound is not None:
            return bound
        from ..repositories.key_value_repository import KeyValueRepository
        filename = Path(os.environ.get("AI4SH_WORKSPACE_DATABASE", str(
            Path(__file__).resolve().parents[2] / "instance" / "workspace.sqlite3"))).resolve()
        with Store._lock:
            if str(filename) not in Store._repositories:
                Store._repositories[str(filename)] = KeyValueRepository(filename)
            return Store._repositories[str(filename)]

    @staticmethod
    def set(key, value):
        Store._repository().set(key, value)

    @staticmethod
    def get(key, default=None):
        return Store._repository().get(key, default)

    @staticmethod
    def set_many(values):
        Store._repository().set_many(values)
