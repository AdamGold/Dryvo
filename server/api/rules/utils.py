import functools

rules_registry = set()


def register_rule(func):
    rules_registry.add(func)

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return func_wrapper
