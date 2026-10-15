"""Domain errors shared by the CLI and future worker."""


class VideoError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
