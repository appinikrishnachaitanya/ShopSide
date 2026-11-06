"""Validated state for a shared move-in mission and exact-cent agreements."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Mission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    household:str=Field(default='',max_length=300)
    country:str=Field(default='',max_length=2)
    currency:str=Field(default='USD',pattern='^[A-Z]{3}$')
    deadline:date|None=None
    budget_cents:int|None=Field(default=None,ge=0,le=100000000,strict=True)
    priorities:list[str]=Field(default_factory=list,max_length=20)
    owned:list[str]=Field(default_factory=list,max_length=30)
    must_have:list[str]=Field(default_factory=list,max_length=30)
    later:list[str]=Field(default_factory=list,max_length=30)
    constraints:list[str]=Field(default_factory=list,max_length=30)

class MissionResponse(BaseModel):
    mission:Mission
    question:str=Field(default='',max_length=500)

class MissionTurn(BaseModel):
    text:str=Field(min_length=1,max_length=2000)
    revision:int
    command_id:str=Field(min_length=1,max_length=100)

class MissionEdit(BaseModel):
    mission:Mission
    revision:int
    command_id:str=Field(min_length=1,max_length=100)

class PlanAction(BaseModel):
    product_id:str=Field(min_length=1,max_length=200)
    status:Literal['proposed','shortlisted','comparing','buy_later']|None=None
    approve:bool|None=None
    revision:int
    command_id:str=Field(min_length=1,max_length=100)
    @model_validator(mode='after')
    def only_one(self):
        if (self.status is None)==(self.approve is None):raise ValueError('Choose status or approval')
        return self

class Allocation(BaseModel):
    total_cents:int=Field(ge=0,le=100000000,strict=True)
    currency:str=Field(pattern='^[A-Z]{3}$')
    shares:dict[str,int]
    revision:int
    command_id:str=Field(min_length=1,max_length=100)
    @model_validator(mode='after')
    def valid_shares(self):
        if not self.shares or any(type(v) is not int or v<0 for v in self.shares.values()) or sum(self.shares.values())!=self.total_cents:raise ValueError('Shares must be nonnegative whole cents totaling the agreed amount')
        return self

class PercentageAllocation(BaseModel):
    total_cents:int=Field(ge=0,le=100000000,strict=True)
    currency:str=Field(pattern='^[A-Z]{3}$')
    basis_points:dict[str,int]
    revision:int
    command_id:str=Field(min_length=1,max_length=100)
    @model_validator(mode='after')
    def valid_percentages(self):
        if not self.basis_points or any(type(v) is not int or v<0 for v in self.basis_points.values()) or sum(self.basis_points.values())!=10000:raise ValueError('Percentages must total 100.00%')
        return self

def allocate_percentages(total_cents:int,percentages:dict[str,int])->dict[str,int]:
    """Largest remainder method; deterministic tie-break by participant name."""
    result={name:total_cents*points//10000 for name,points in percentages.items()}
    remaining=total_cents-sum(result.values())
    order=sorted(percentages,key=lambda name:(-(total_cents*percentages[name]%10000),name))
    for name in order[:remaining]:result[name]+=1
    return result

class RelocationPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    allowance_cents:int=Field(ge=0,le=100000000,strict=True)
    currency:Literal['USD']='USD'
    eligible_categories:list[str]=Field(min_length=1,max_length=20)
    approval_threshold_cents:int=Field(ge=0,le=100000000,strict=True)
    @model_validator(mode='after')
    def clean_categories(self):
        if any(not x.strip() or len(x)>80 for x in self.eligible_categories):raise ValueError('Invalid category')
        self.eligible_categories=sorted(set(x.strip().lower() for x in self.eligible_categories))
        return self

def policy_eligibility(policy:RelocationPolicy,category:str,amount_cents:int,currency:str,spent_cents:int)->dict:
    if currency!=policy.currency:return {'eligible':False,'reason':'Currency does not match the allowance','approval_required':False}
    if category.strip().lower() not in policy.eligible_categories:return {'eligible':False,'reason':'Category is not eligible','approval_required':False}
    if amount_cents<0 or spent_cents+amount_cents>policy.allowance_cents:return {'eligible':False,'reason':'Allowance would be exceeded','approval_required':False}
    return {'eligible':True,'reason':'Meets the illustrative policy','approval_required':amount_cents>policy.approval_threshold_cents}

class PolicyCheck(BaseModel):
    product_id:str=Field(min_length=1,max_length=200)
    revision:int
