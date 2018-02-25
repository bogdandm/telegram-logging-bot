import os


def get_env(key: str) -> str:
    value = os.environ.get(key)

    if value.startswith("/"):
        pass  # TODO: read from filesystem (Docker secrets support)
    return value
