import importlib
import random
import string
from typing import Iterable, List

DEFAULT_CHAR_STRING = string.ascii_lowercase + string.digits


def generate_random_string(chars=DEFAULT_CHAR_STRING, size=6) -> str:
    return "".join(random.choice(chars) for _ in range(size))


def compact(iterable: Iterable) -> List:
    """
    :returns new collection without False values
    """
    return [x for x in iterable if x]


def percentage(part, whole) -> str:
    return f"{100 * float(part) / float(whole)}%"


def import_attribute(path):
    """import by fully-qualified name"""
    assert isinstance(path, str)
    pkg, attr = path.rsplit(".", 1)
    ret = getattr(importlib.import_module(pkg), attr)
    return ret
