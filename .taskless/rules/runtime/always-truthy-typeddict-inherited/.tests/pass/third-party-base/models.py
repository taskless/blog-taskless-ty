from somelib import Record


class User(Record):
    name: str


def save(user: User):
    if not user:
        return
