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
