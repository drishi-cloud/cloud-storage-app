from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy import func
from app.core.database import Base
import enum

class PermissionRole(str, enum.Enum):
    editor="editor"
    viewer="viewer"
    
class Share(Base):
    __tablename__="shares"
    
    id=Column(Integer, primary_key=True, index=True)
    file_id=Column(Integer, ForeignKey("files.id"),nullable=False)
    folder_id=Column(Integer, ForeignKey("folders.id"),nullable=True)
    
    shared_with_user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    shared_by_user_id=Column(Integer, ForeignKey("users.id"),nullable=  False)
    
    role=Column(Enum(PermissionRole),nullable=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())