from enum import Enum

class Choice(Enum):
    FIRST = 1
    SECOND = 2

class Falsy(Enum):
    ZERO = 0
    ONE = 1
    def __bool__(self):
        return bool(self.value)

def f(choice: Choice, other: Falsy):
    if choice:
        pass
    if other:
        pass
