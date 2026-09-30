from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class SummaryCard(BaseModel):
    label: str
    value: str
    trend: str


class DashboardResponse(BaseModel):
    total_users: int
    active_projects: int
    revenue: str
    conversion: str
    cards: list[SummaryCard]


@router.get("", response_model=DashboardResponse)
def get_dashboard():
    return {
        "total_users": 128,
        "active_projects": 24,
        "revenue": "R$ 48.250,00",
        "conversion": "8.4%",
        "cards": [
            {"label": "Novos usuários", "value": "+18%", "trend": "up"},
            {"label": "Projetos ativos", "value": "24", "trend": "up"},
            {"label": "Taxa de conversão", "value": "8.4%", "trend": "up"},
            {"label": "Pendências", "value": "7", "trend": "down"},
        ],
    }
