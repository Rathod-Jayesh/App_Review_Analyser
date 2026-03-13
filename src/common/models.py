from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReviewSource(str, Enum):
    PLAY_STORE = "play_store"
    APP_STORE = "app_store"


class Review(BaseModel):
    id: str
    rating: int = Field(ge=1, le=5)
    text: str
    date: str


class ReviewStore(BaseModel):
    last_fetched: str
    total_count: int
    reviews: list[Review] = Field(default_factory=list)


class FetchConfig(BaseModel):
    weeks: int = Field(default=12, ge=1, le=52)
    max_reviews: int = Field(default=3000, ge=100, le=5000)
    sources: list[ReviewSource] = Field(
        default_factory=lambda: [ReviewSource.PLAY_STORE]
    )


class FetchResult(BaseModel):
    total_count: int
    sources: dict[str, int]
    date_range: dict[str, str]


# ─── Phase 2 Models ───


class Theme(BaseModel):
    id: str
    name: str
    description: str


class ThemeStore(BaseModel):
    generated_at: str
    review_count_used: int
    themes: list[Theme] = Field(default_factory=list)


# ─── Phase 2b Models ───


class ClassifiedReview(BaseModel):
    review_id: str
    theme_id: str
    confidence: float = Field(ge=0, le=1)


class ClassificationStore(BaseModel):
    classified_at: str
    total_classified: int
    theme_distribution: dict[str, int] = Field(default_factory=dict)
    classifications: list[ClassifiedReview] = Field(default_factory=list)


# ─── Phase 3 Models ───


class PulseNote(BaseModel):
    report_date: str
    period_start: str
    period_end: str
    total_reviews: int
    average_rating: float
    markdown_content: str
    plaintext_content: str
    generated_at: str
    md_file: str = ""
    txt_file: str = ""


# ─── Phase 4 Models ───


class EmailDraft(BaseModel):
    to: str
    subject: str
    html_body: str
    plain_body: str
    generated_at: str
    report_date: str
    eml_file: str = ""


