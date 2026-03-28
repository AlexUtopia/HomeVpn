

def apply_decorators(decorators_list):
    """A decorator that applies a list of other decorators."""

    def decorator(func):
        # Apply each decorator in reverse order
        for dec in reversed(decorators_list):
            func = dec(func)
        return func

    return decorator
