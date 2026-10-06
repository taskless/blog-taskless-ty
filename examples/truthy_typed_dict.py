from typing import TypedDict


class Foo(TypedDict):
    X: int


class Bar(Foo):
    Y: int


class Empty(TypedDict, total=False):
    Z: int


def check(x: Bar):
    if not x:
        print("empty dictionary")


def ok(x: Empty):
    if not x:
        print("can be empty")


def direct(x: Foo):
    if not x:
        pass
