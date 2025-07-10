from pydantic import BaseModel
from typing import Optional

class Scenarioes(BaseModel):
    request1: Optional[str]
    request2: Optional[str]
    senarioe: Optional[str]