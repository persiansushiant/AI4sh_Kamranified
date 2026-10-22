from contextvars import ContextVar
from .log_bridge import notebook_services

_current = ContextVar("shell_services")


def bind(services):
    return _current.set(services)


def unbind(token):
    _current.reset(token)


def services():
    try:
        return _current.get()
    except LookupError:
        return notebook_services