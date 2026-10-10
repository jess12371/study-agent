# Skema Pydantic untuk fitur F-06: Resource Recommendation.

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ResourceCreate(BaseModel):
    # Data untuk menambah resource (dipakai seed).
    topic: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=300)
    url: str | None = None
    level: str | None = Field(default=None, max_length=50)
    is_free: bool = True
    description: str | None = None
    skills: list[str] = Field(default_factory=list)


class ResourceResponse(BaseModel):
    # Resource yang dikembalikan ke client (dengan skor kemiripan).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    type: str | None = None
    name: str
    url: str | None = None
    level: str | None = None
    is_free: bool
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    similarity_score: float | None = None
    # high (>=0.6) / medium (0.4-0.6) / low (<0.4).
    relevance_label: str | None = None


class ResourceSearchRequest(BaseModel):
    # Parameter pencarian resource.
    query: str = ""
    topic: str | None = None
    level: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.4, ge=0.0, le=1.0)
