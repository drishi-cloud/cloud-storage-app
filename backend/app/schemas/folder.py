from pydantic import BaseModel
from typing import Optional
from app.schemas.file import FileResponse

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int]=None
    
class FolderResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    created_at: str
    
    class Config:
        from_attributes=True
        
class FolderContentsResponse(BaseModel):
    folders: list[FolderResponse]
    files:list[FileResponse]
    
class BreadcrumbItem(BaseModel):
    id: int
    name: str
    
class BreadcrumbResponse(BaseModel):
    path: list[BreadcrumbItem]
    
class FolderRename(BaseModel):
    name:str
    
class FolderMove(BaseModel):
    parent_id: Optional[int]=None
        
