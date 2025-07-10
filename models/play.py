from pydantic import BaseModel
from typing import Optional

class Scenarioes(BaseModel):
    request1: Optional[str] = None
    request2: Optional[str] = None
    senarioe: Optional[str] = None

class CreateGameRequest(BaseModel):
    scenarioes: str

class CreateGameResponse(BaseModel):
    user_id: str
    game_id: str
    struct: Optional[dict] = None
    funds: int
    current_month: int
    scenarioes: str
    is_finished: bool
    created_at: str