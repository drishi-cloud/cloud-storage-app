from pydantic import BaseModel

class LinkShareCreate(BaseModel):
    file_id: int
    expires_in_hours: int = 24   

class LinkShareResponse(BaseModel):
    token: str
    expires_at: str

class PublicFileInfo(BaseModel):
    filename: str
    file_type: str
    file_size: int
    download_url: str