"""Reusable pagination envelope with Link header support."""

from typing import Generic, List, TypeVar

from fastapi import Response
from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta


def paginate(items: List, total: int, limit: int, offset: int) -> dict:
    return {
        "data": items,
        "meta": PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ).model_dump(),
    }


def add_pagination_headers(
    response: Response, offset: int, limit: int, total: int, base_url: str
):
    """Add RFC 8288 Link headers for next/prev pagination."""
    links = []
    if offset + limit < total:
        next_offset = offset + limit
        links.append(f'<{base_url}?limit={limit}&offset={next_offset}>; rel="next"')
    if offset > 0:
        prev_offset = max(0, offset - limit)
        links.append(f'<{base_url}?limit={limit}&offset={prev_offset}>; rel="prev"')
    if links:
        response.headers["Link"] = ", ".join(links)
