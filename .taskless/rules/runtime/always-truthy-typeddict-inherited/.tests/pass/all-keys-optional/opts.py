from typing import TypedDict
from typing_extensions import NotRequired


class Options(TypedDict, total=False):
    verbose: bool


class MoreOptions(Options):
    color: "NotRequired[str]"


def run(opts: MoreOptions):
    if not opts:
        return
