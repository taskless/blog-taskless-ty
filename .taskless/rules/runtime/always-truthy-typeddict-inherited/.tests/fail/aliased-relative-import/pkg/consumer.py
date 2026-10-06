from .events import Event as Payload


def consume(payload: Payload) -> str:
    return "full" if payload else "empty"
