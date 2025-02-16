import re


def to_snake_case(event_name: str) -> str:
    result = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", event_name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", result).lower()
