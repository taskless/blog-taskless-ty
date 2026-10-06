class Foo:
    def __init__(self):
        self.x: tuple[int] = (42,)

    def method(self) -> None:
        if self.x:
            print("tuple is empty")

def g(a: tuple[int, ...], b: tuple[int, str], c: tuple[()]) -> tuple[str]:
    return ("a",)
