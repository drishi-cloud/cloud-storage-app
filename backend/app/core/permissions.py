from enum import Enum
from typing import Optional
from sqlalchemy.orm import Session
from app.models.file import File
from app.models.folder import Folder
from app.models.share import Share, PermissionRole

class AccessLevel(str, Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"
    none = "none"
    
_LEVEL_RANK={
    AccessLevel.none:0,
    AccessLevel.viewer:1,
    AccessLevel.editor:2,
    AccessLevel.owner:3
}

def get_file_access_level(file: File, user_id: int, db:Session)->AccessLevel:
    if file.owner_id==user_id:
        return AccessLevel.owner
    
    direct_share=db.query(Share).filter(
        Share.file_id==file.id,
        Share.shared_with_user_id==user_id
    ).first()
    
    if direct_share:
        return AccessLevel.editor if direct_share.role==PermissionRole.editor else AccessLevel.viewer
    
    if file.folder_id is not None:
        folder_share=db.query(Share).filter(
            Share.folder_id==file.folder_id,
            Share.shared_with_user_id==user_id
        ).first()
        
        if folder_share:
            return AccessLevel.editor if folder_share.role==PermissionRole.editor else AccessLevel.viewer
        return AccessLevel.none
    
def get_folder_access_level(folder: Folder, user_id:int, db:Session)->AccessLevel:
    if folder.owner_id==user_id:
        return AccessLevel.owner
    direct_share=db.query(Share).filter(
        Share.folder_id==folder.id,
        Share.shared_with_user_id==user_id
    ).first()
    
    if direct_share:
        return AccessLevel.editor if direct_share.role==PermissionRole.editor else AccessLevel.viewer
    
    return AccessLevel.none

def has_at_least(level: AccessLevel, required: AccessLevel)->bool:
    return _LEVEL_RANK[level]>=_LEVEL_RANK[required]