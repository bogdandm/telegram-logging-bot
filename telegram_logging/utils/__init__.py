import os


def get_env(key: str, default=None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise AttributeError("Param '{}' is not set correctly".format(key))

    if value.startswith("/"):
        with open(value) as f:
            value = f.read()

    return value
