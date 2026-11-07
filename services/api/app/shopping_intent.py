"""Structured interpretation of a shared shopping request."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

SIZE_ONLY = re.compile(r'^(?:(?:us|uk|eu)\s+)?size\s*[:#-]?\s*([a-z]{1,3}|\d{1,3}(?:\.\d)?)$', re.I)
OUTFIT_PIECES = {
    'dress':'shoes','suit':'dress shoes','tuxedo':'dress shoes',
    'saree':'sandals','lehenga':'sandals','jumpsuit':'shoes',
    'kurta':'shoes','sherwani':'dress shoes',
}

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


def complete_outfit_intent(intent:ShoppingIntent,original_request:str,answer:str='')->ShoppingIntent:
    """Complete an explicitly requested outfit only after the main garment is known."""
    if not re.search(r'\b(?:outfit|look|ensemble)\b',original_request,re.I):return intent
    if not answer or re.search(r'\b(?:only|just one item)\b',answer,re.I):return intent
    match=next(((piece,companion) for piece,companion in OUTFIT_PIECES.items()
                if re.search(r'\b'+re.escape(piece)+r'\b',answer,re.I)),None)
    if not match:return intent
    piece,companion=match
    requirements=[item for item in intent.product_requirements if not re.fullmatch(r'(?:wedding\s+)?(?:outfit|look|ensemble)',item.strip(),re.I)]
    if not any(re.search(r'\b'+re.escape(piece)+r'\b',item,re.I) for item in requirements):requirements.insert(0,piece)
    if len(requirements)==1:requirements.append(companion)
    intent.product_requirements=requirements[:4]
    intent.bundle_requested=len(intent.product_requirements)>1
    if intent.bundle_requested:intent.follow_up=''
    return intent
