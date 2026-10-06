from typing import TypedDict


class Base(TypedDict):
    id: int


class Order(Base):
    total: float
