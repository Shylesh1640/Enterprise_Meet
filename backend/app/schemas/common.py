"""Enterprise Meet — Common Pydantic schemas: API response, pagination, errors."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Standard API Response ─────────────────────────────────────────────────────

class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope used by ALL endpoints.
    Matches the spec:
        { success, message, data, errors, timestamp, request_id }
    """

    success: bool = True
    message: str = "OK"
    data: Optional[T] = None
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def ok(cls, data: Any = None, message: str = "OK", request_id: str = "") -> "APIResponse":
        return cls(success=True, message=message, data=data, request_id=request_id)

    @classmethod
    def fail(cls, message: str, errors: List[str] | None = None, request_id: str = "") -> "APIResponse":
        return cls(
            success=False,
            message=message,
            data=None,
            errors=errors or [message],
            request_id=request_id,
        )

    model_config = {"from_attributes": True}


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_total(cls, total: int, page: int, page_size: int) -> "PaginationMeta":
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with metadata."""

    items: List[T]
    pagination: PaginationMeta

    model_config = {"from_attributes": True}


# ── Sort / Filter ─────────────────────────────────────────────────────────────

class SortOrder(str):
    ASC = "asc"
    DESC = "desc"


# ── Health ────────────────────────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    service: str
    status: str
    details: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: List[ServiceHealth] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
