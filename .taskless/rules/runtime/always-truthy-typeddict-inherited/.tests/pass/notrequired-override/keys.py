from typing import TypedDict
from typing_extensions import NotRequired


class Keys(TypedDict):
    a: NotRequired[int]
    b: NotRequired[str]


def use(keys: Keys):
    if keys:
        pass
