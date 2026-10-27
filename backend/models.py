"""Request / response schemas for the Knowledge Inbox API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    type: Literal["note", "url"]
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be empty")
        return cleaned


class ItemResponse(BaseModel):
    id: int
    source_type: Literal["note", "url"]
    source: str
    preview: str
    created_at: datetime


class IngestResponse(BaseModel):
    item: ItemResponse
    message: str = "ingested"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be empty")
        return cleaned


class SourceSnippet(BaseModel):
    item_id: int
    source_type: Literal["note", "url"]
    source: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceSnippet]
