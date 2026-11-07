"""Structured interpretation of a shared shopping request."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

SIZE_ONLY = re.compile(r'^(?:(?:us|uk|eu)\s+)?size\s*[:#-]?\s*([a-z]{1,3}|\d{1,3}(?:\.\d)?)$', re.I)

class ShoppingIntent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    shopping_goal: str = Field(default='', max_length=300)
    product_requirements: list[str] = Field(default_factory=list, max_length=12)
    budget_cents: int | None = Field(default=None, ge=0, le=100000000, strict=True)
    currency: str | None = Field(default=None, pattern='^[A-Z]{3}$')
    style: str = Field(default='', max_length=200)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    hard_constraints: dict[str,str] = Field(default_factory=dict,max_length=12)
    preferences: dict[str,str] = Field(default_factory=dict,max_length=12)
    shopping_context: Literal['general','move_in'] = 'general'
    participant_count: int | None = Field(default=None, ge=1, le=4, strict=True)
    bundle_requested: bool = False
    follow_up: str = Field(default='', max_length=300)

    @model_validator(mode='after')
    def keep_sizes_out_of_product_requirements(self):
        products=[]
        for requirement in self.product_requirements:
            match=SIZE_ONLY.fullmatch(requirement.strip())
            if match:
                constraint=requirement.strip()
                if constraint not in self.constraints:
                    self.constraints.append(constraint)
            else:
                products.append(requirement)
        self.product_requirements=products
        return self
