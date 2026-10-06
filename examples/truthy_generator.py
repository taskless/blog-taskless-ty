def f(items: list[int]):
    if (item > 42 for item in items):
        pass
    if any(item > 42 for item in items):
        pass
    gen = (i for i in items)
    if gen:
        pass
    while (i for i in items):
        break
    assert (i for i in items)
