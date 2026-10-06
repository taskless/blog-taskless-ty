class Item:
    sku: str

    def __bool__(self) -> bool:
        return bool(self.sku)
