from pydantic import BaseModel
from typing import Optional, Dict, List

class ScenarioSummary(BaseModel):
    scenario_id: str
    name: str
    end_month: int
    current_month: int
    feature_count: int
    created_at: str

class ScenarioDetail(BaseModel):
    scenario: str
    requests: Dict[str, str]

class ScenarioesData(BaseModel):
    first_scenario: ScenarioDetail

class Scenarioes(BaseModel):
    scenarioes: ScenarioesData

class CreateGameRequest(BaseModel):
    scenarioes: str
    game_name: Optional[str] = None

class CreateGameResponse(BaseModel):
    user_id: str
    game_id: str
    struct: Optional[dict] = None
    funds: int
    current_month: int
    scenarioes: str
    is_finished: bool
    created_at: str

class GetGameResponse(BaseModel):
    user_id: str
    game_id: str
    struct: Optional[dict] = None
    funds: int
    current_month: int
    scenarioes: str
    is_finished: bool
    created_at: str

class UpdateGameRequest(BaseModel):
    data: dict

class GetStructResponse(BaseModel):
    struct: Optional[dict] = None

