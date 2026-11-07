"""Structured interpretation of a shared shopping request."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ShoppingIntent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    shopping_goal: str = Field(default='', max_length=300)
    product_requirements: list[str] = Field(default_factory=list, max_length=12)
    budget_cents: int | None = Field(default=None, ge=0, le=100000000, strict=True)
    currency: str | None = Field(default=None, pattern='^[A-Z]{3}$')
    style: str = Field(default='', max_length=200)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    shopping_context: Literal['general','move_in'] = 'general'
    participant_count: int | None = Field(default=None, ge=1, le=4, strict=True)
    bundle_requested: bool = False
    follow_up: str = Field(default='', max_length=300)
