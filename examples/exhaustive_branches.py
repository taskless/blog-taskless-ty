def branchy(x: int | str):
    if isinstance(x, int):
        print("it's an int")
    elif isinstance(x, str):
        print("it's a str")
