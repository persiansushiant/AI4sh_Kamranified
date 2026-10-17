# Public configuration persistence facade. Delegates storage to the repository bound to this workspace.
from .workspace_context import services

class Store:
    @staticmethod
    # Save a JSON-serializable value under a stable namespaced key.
    def set(key, value):
        services().store.set(key, value)

    @staticmethod
    # Read a stored value; use the default only when the key is absent.
    def get(key, default=None):
        return services().store.get(key, default)

    @staticmethod
    # Save related values in one repository transaction, such as data and its completion flag.
    def set_many(values):
        services().store.set_many(values)
