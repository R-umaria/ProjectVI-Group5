from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ApiError(Exception):
    """Raise to return a consistent JSON error response."""

    status_code: int
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self, request_id: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details or {},
                "request_id": request_id,
            }
        }
        return payload


def abort_json(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Convenience wrapper."""
    raise ApiError(status_code=status_code, code=code, message=message, details=details)
