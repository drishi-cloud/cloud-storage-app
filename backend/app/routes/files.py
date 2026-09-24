import uuid
from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.supabase_client import supabase,SUPABASE_BUCKET_NAME
from app.models.user import User
from app.models.file import File
from app.schemas.file import UploadCompleteRequest, UploadInitRequest,UploadInitResponse,FileResponse

router=APIRouter(prefix="/files",tags=["Files"])

@router.post("/upload-init",response_model=UploadInitResponse)
def upload_init(request: UploadInitRequest, current_user: User=Depends(get_current_user),
                db:Session=Depends(get_db)):
    unique_id=uuid.uuid4().hex
    storage_key=f"users/{current_user.id}/{unique_id}_{request.filename}"
    
    try:
        signed_response=supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_upload_url(storage_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate upload URL:{str(e)}")
    
    upload_url=signed_response["signed_url"]
    return UploadInitResponse(upload_url=upload_url,storage_key=storage_key)

@router.post("/upload-complete",response_model=FileResponse)
def upload_complete(request: UploadCompleteRequest, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    try:
        folder_path="/".join(request.storage_key.split("/")[:-1])
        file_name_only=request.storage_key.split("/")[-1]
        files_in_folder=supabase.storage.from_(SUPABASE_BUCKET_NAME).list(folder_path)
        file_exists=any(f["name"]==file_name_only for f in files_in_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not verify upload: {str(e)}")
    
    if not file_exists:
        raise HTTPException(status_code=400, detail="File not found in storage. Did the upload actually complete?")
    
    new_file=File(
        filename=request.filename,
        file_type=request.file_type,
        file_size=request.file_size,
        storage_key=request.storage_key,
        owner_id=current_user.id,
        folder_id=request.folder_id
    )
    
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    
    return FileResponse(
        id=new_file.id,
        filename=new_file.filename,
        file_type=new_file.file_type,
        file_size=new_file.file_size,
        folder_id=new_file.folder_id,
        created_at=str(new_file.created_at)
    )
    