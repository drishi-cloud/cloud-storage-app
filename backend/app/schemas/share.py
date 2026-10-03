from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.schemas.file import FileResponse
from app.schemas.folder import FolderResponse
from app.models.share import PermissionRole

class ShareCreate(BaseModel):
    email: EmailStr
    role: PermissionRole
    file_id: Optional[int]=None
    folder_id: Optional[int]=None
    
class ShareResponse(BaseModel):
    id: int
    file_id: Optional[int]
    folder_id: Optional[int]
    shared_with_user_id: int
    shared_with_email: str
    role: PermissionRole
    created_at: str
    
    class Config:
        from_attributes=True
        
class SharedFileItem(BaseModel):
    share_id: int
    role: PermissionRole
    owner_email: str
    file: FileResponse

class SharedFolderItem(BaseModel):
    share_id: int
    role: PermissionRole
    owner_email: str
    folder: FolderResponse
    
class SharedWithMeResponse(BaseModel):
    files: List[SharedFileItem]
    folders: List[SharedFolderItem]
    
class ShareListItem(BaseModel):
    share_id: int
    shared_with_email: str
    role: PermissionRole
    created_at: str

class ShareListResponse(BaseModel):
    shares: List[ShareListItem]

class ShareUpdateRole(BaseModel):
    role: PermissionRole