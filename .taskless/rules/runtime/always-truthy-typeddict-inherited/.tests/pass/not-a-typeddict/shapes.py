class Shape:
    def __len__(self) -> int:
        return 0


class Square(Shape):
    side: int


def draw(s: Square):
    if not s:
        return
