from pydantic import BaseModel
from typing import Optional, Dict, List, Any

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
    scenario_id: ScenarioesData

class CreateGameRequest(BaseModel):
    scenario_id: str
    game_name: Optional[str] = None

class CreateGameResponse(BaseModel):
    user_id: str
    game_id: str
    struct: Optional[dict] = None
    funds: int
    current_month: int
    scenario_id: str
    is_finished: bool
    created_at: str

class GetGameResponse(BaseModel):
    user_id: str
    game_id: str
    struct: Optional[dict] = None
    funds: int
    current_month: int
    scenario_id: str
    is_finished: bool
    created_at: str

class GetGameResponses(BaseModel):
    games: List[GetGameResponse]

class UpdateGameRequest(BaseModel):
    struct: dict

class GetStructResponse(BaseModel):
    struct: Optional[dict] = None

