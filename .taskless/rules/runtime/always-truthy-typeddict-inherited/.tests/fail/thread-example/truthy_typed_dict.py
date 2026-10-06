from typing import TypedDict


class Foo(TypedDict):
    X: int


class Bar(Foo):
    Y: int


def check(x: Bar):
    if not x:
        print("empty dictionary")
