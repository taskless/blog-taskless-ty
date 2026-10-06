from typing import TypedDict
from typing_extensions import Required


class Settings(TypedDict, total=False):
    debug: bool
    name: Required[str]


def load(settings: Settings):
    while settings and True:
        break
