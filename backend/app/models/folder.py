from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class Folder(Base):
    __tablename__="folders"
    
    id=Column(Integer, primary_key=True, index=True)
    name=Column(String, nullable=False)
    owner_id=Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id=Column(Integer, ForeignKey("folders.id"),nullable=True)
    is_deleted=Column(Boolean, default=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())