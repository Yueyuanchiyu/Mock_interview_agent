from __future__ import annotations


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

