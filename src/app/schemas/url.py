from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


class URLShortenRequest(BaseModel):
    long_url: HttpUrl = Field(
        ...,
        description="The original URL to shorten",
        examples=["https://www.example.com/long_url/path"]
    )


class URLShortenResponse(BaseModel):

    short_code: str = Field(
        ...,
        description="The generated short code",
        examples=["abc123"]
    )
    short_url: str = Field(
        ...,
        description="The complete short URL",
        examples=["http://localhost:8000/abc123"]
    )
    original_url: str = Field(
        ...,
        description="The original URL",
        examples=["https://www.example.com/long_url/path"]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the short URL was created"
    )


class URLStatsResponse(BaseModel):

    short_code: str = Field(
        ...,
        description="The short code",
        examples=["abc123"]
    )
    original_url: str = Field(
        ...,
        description="The original URL",
        examples=["https://www.example.com/long_url/path"]
    )
    total_visits: int = Field(
        ...,
        description="Total number of visits",
        examples=[42]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the short URL was created"
    )