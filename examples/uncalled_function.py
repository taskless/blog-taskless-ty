def condition(): ...

if condition:
    pass
else:
    print("Unreachable!")

# should NOT fire: called
if condition():
    pass

# should NOT fire: shadowed by a param
def h(condition):
    if condition:
        pass

# should fire: while / ternary / and
while condition:
    break
x = 1 if condition else 2
if condition and True:
    pass
