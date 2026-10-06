async def f(): ...

async def g():
    if f:
        print("foo")
    # forgotten await: coroutine is truthy
    if f():
        print("bar")
    # fine
    if await f():
        print("baz")
