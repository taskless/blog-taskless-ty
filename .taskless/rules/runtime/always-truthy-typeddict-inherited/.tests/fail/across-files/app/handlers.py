from app.models import Order


def handle(order: Order) -> None:
    if not order:
        return
