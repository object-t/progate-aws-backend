from pydantic import BaseModel
from typing import Optional, Dict, List

class SharedStructure(BaseModel):
    structure_id: str
    title: str
    data: Dict
    description: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    is_public: bool = True
    created_at: str
    updated_at: str

class SharedStructureSummary(BaseModel):
    structure_id: str
    title: str
    description: Optional[str] = None
    author_name: Optional[str] = None
    created_at: str
    updated_at: str

class CreateSharedStructureRequest(BaseModel):
    title: str
    data: Dict
    description: Optional[str] = None
    is_public: bool = True

class UpdateSharedStructureRequest(BaseModel):
    data: Dict

class CreateSharedStructureResponse(BaseModel):
    structure_id: str
    message: str

class SharedStructuresResponse(BaseModel):
    structures: List[SharedStructureSummary]
    total_count: int
    page: int
    page_size: int
    has_next: bool