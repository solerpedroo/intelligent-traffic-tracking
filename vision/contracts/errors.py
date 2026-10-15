"""Transport-independent errors exposed by processing adapters."""


class VisionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
