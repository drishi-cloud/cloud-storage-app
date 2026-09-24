from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class File(Base):
    __tablename__="files"
    
    id=Column(Integer, primary_key=True, index=True)
    filename=Column(String, nullable=False)
    file_type=Column(String, nullable=False)
    file_size=Column(BigInteger, nullable=False)
    storage_key=Column(String, nullable=False, unique=True)
    
    owner_id=Column(Integer, ForeignKey("users.id"),nullable=False)
    folder_id=Column(Integer, ForeignKey("folders.id"),nullable=True)
    
    is_deleted=Column(Boolean, default=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    