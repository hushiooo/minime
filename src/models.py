from datetime import datetime

from pydantic import BaseModel


class URLMapping(BaseModel):
    slug: str
    original_url: str
    created_at: datetime


class RateLimit(BaseModel):
    ip_address: str
    request_count: int
    last_request: datetime
