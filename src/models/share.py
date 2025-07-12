from pydantic import BaseModel
from typing import Optional, Dict, List

class SharedStructure(BaseModel):
    user_id: str
    sandbox_id: str
    struct: dict
    is_public: bool = True
    created_at: str

class SharedStructureSummary(BaseModel):
    user_id: str
    sandbox_id: str
    struct: dict
    is_published: bool
    created_at: str

class CreateSharedStructureRequest(BaseModel):
    title: str
    data: Dict
    description: Optional[str] = None
    is_public: bool = True

class UpdateSharedStructureRequest(BaseModel):
    struct: dict

class SharedStructuresResponse(BaseModel):
    structures: List[SharedStructureSummary]
    total_count: int
    page: int
    page_size: int
    has_next: bool
