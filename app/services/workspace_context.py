# Context-local binding for public workspace controls. Framework entry points bind the runtime;
# arbitrary threads or scripts do not automatically receive a binding.
from contextvars import ContextVar

_current = ContextVar("shell_services")

# Bind a runtime to the current context and return a token for later restoration.
def bind(services):
    return _current.set(services)

# Restore the previous binding using the token returned by bind().
def unbind(token):
    _current.reset(token)

# Return the currently bound runtime or raise a clear error outside framework context.
def services():
    try:
        return _current.get()
    except LookupError:
        raise RuntimeError("Shell API must be called in configure() or an activity") from None

