from pydantic import BaseModel, field_validator
from typing import Optional

MAX_FILE_SIZE=50*1024*1024
ALLOWED_FILE_TYPES=[
    "image/png","image/jpeg","image/gif",
    "application/pdf",
    "application/msword",
    "text/plain",
    "application/zip",
]
class UploadInitRequest(BaseModel):
    filename:str
    file_type:str
    file_size:int
    folder_id: Optional[int]=None
    
    @field_validator("file_size")
    @classmethod
    def check_file_size(cls,value):
        if value>MAX_FILE_SIZE:
            raise ValueError(f"File too large.Max allowed file size is {MAX_FILE_SIZE//(1024*1024)}MB")
        return value
    
    @field_validator("file_type")
    @classmethod
    def check_file_type(cls,value):
        if value not in ALLOWED_FILE_TYPES:
            raise ValueError(f"File type '{value}' is not allowed.")
        return value
    
class UploadInitResponse(BaseModel):
    upload_url:str
    storage_key:str
    
class UploadCompleteRequest(BaseModel):
    filename: str
    file_type: str
    file_size: int
    storage_key: str
    folder_id: Optional[int]=None
    
class FileResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    folder_id: Optional[int]
    
    class Config:
        from_attributes=True