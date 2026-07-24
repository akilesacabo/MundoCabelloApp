from src.exceptions import NotFound


class ItemNotFound(NotFound):
    detail = "Item not found"
