from typing import TypedDict as TD


class Conf(TD):
    path: str


def read(conf: Conf):
    if conf:
        pass
