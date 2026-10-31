from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from qpf import preflight

router = APIRouter()
Pref = Literal["risk_first", "balanced", "return_first"]


class GroverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marked: str = Field(default="1010", pattern=r"^[01]{4}$")
    budget: float = Field(default=0.2, ge=0.0, le=0.5, allow_inf_nan=False)


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preference: Pref = "risk_first"
    other: Pref = "return_first"


@router.post("/usecases/grover")
def grover(body: GroverRequest):
    return preflight.grover_check(body.marked, budget=body.budget)


@router.post("/usecases/portfolio")
def portfolio(body: PortfolioRequest):
    try:
        return preflight.portfolio_check(body.preference, body.other)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
