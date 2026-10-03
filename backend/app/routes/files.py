from fileinput import filename
from http.client import HTTP_PORT
import uuid
from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.supabase_client import supabase,SUPABASE_BUCKET_NAME
from app.models.user import User
from app.models.file import File
from app.schemas.file import UploadCompleteRequest, UploadInitRequest,UploadInitResponse,FileResponse, FileRename, FileMove
from app.models.folder import Folder
from app.core.permissions import (get_file_access_level,get_folder_access_level,has_at_least, AccessLevel)

router=APIRouter(prefix="/files",tags=["Files"])

def _file_response(f:File)->FileResponse:
    return FileResponse(
        id=f.id, filename=f.filename, file_type=f.file_type,
        file_size=f.file_size, folder_id=f.folder_id, created_at=str(f.created_at)
    )
    
@router.post("/upload-init",response_model=UploadInitRequest)
def upload_init(
    request: UploadInitRequest, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)
):
    if request.folder_id is not None:
        folder=db.query(Folder).filter(
            Folder.id==request.folder_id, 
            Folder.is_deleted==False
        ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    access=get_folder_access_level(folder, current_user.id,db)
    if not has_at_least(access, AccessLevel.editor):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    unique_id=uuid.uuid4().hex
    storage_key=f"users/{current_user.id}/{unique_id}_{request.filename}"
    
    try:
        signed_response=supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_upload_url(storage_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate upload URL:{str(e)}")
    
    return UploadInitResponse(
        upload_url=signed_response["signed_url"],
        storage_key=storage_key
    )
    
@router.post("/upload-complete",response_model=FileResponse)
def upload_complete(
    request: UploadCompleteRequest,
    current_user: User=Depends(get_current_user),
    db: Session=Depends(get_db)
):
    if request.folder_id is not None:
        folder=db.query(Folder).filter(
            Folder.id==request.folder_id,
            Folder.is_deleted==False
        ).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
    try:
        folder_path="/".join(request.storage_key.split("/"))[:1]
        file_name_only=request.storage.key.split("/")[-1]
        files_in_folder=supabase.storage.from_(SUPABASE_BUCKET_NAME).list(folder_path)
        file_exists=any(f["name"]==file_name_only for f in files_in_folder)
    except Exception as e:
        raise HTTPException(status_code=500, deatil=f"Could not verify upload: {str(e)}")
    
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
    
    return _file_response(new_file)

@router.patch("/{file_id}/rename", response_model=FileResponse)
def rename_file(
    file_id: int,
    request: FileRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    access = get_file_access_level(file_record, current_user.id, db)
    if not has_at_least(access, AccessLevel.editor):
        raise HTTPException(status_code=404, detail="File not found")

    file_record.filename = request.filename
    db.commit()
    db.refresh(file_record)
    return _file_response(file_record)


@router.patch("/{file_id}/move", response_model=FileResponse)
def move_file(
    file_id: int,
    request: FileMove,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    access = get_file_access_level(file_record, current_user.id, db)
    if not has_at_least(access, AccessLevel.editor):
        raise HTTPException(status_code=404, detail="File not found")

    if request.folder_id is not None:
        destination = db.query(Folder).filter(
            Folder.id == request.folder_id, Folder.is_deleted == False
        ).first()
        if not destination:
            raise HTTPException(status_code=404, detail="Destination folder not found")

        dest_access = get_folder_access_level(destination, current_user.id, db)
        if not has_at_least(dest_access, AccessLevel.editor):
            raise HTTPException(status_code=404, detail="Destination folder not found")

    file_record.folder_id = request.folder_id
    db.commit()
    db.refresh(file_record)
    return _file_response(file_record)


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    access = get_file_access_level(file_record, current_user.id, db)
    if not has_at_least(access, AccessLevel.owner):
        raise HTTPException(status_code=404, detail="File not found")

    file_record.is_deleted = True
    db.commit()
    return {"message": "File moved to trash", "id": file_id}


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    access = get_file_access_level(file_record, current_user.id, db)
    if not has_at_least(access, AccessLevel.viewer):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        signed_response = supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_url(
            file_record.storage_key, 60
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate download URL: {str(e)}")

    return {
        "download_url": signed_response["signedURL"],
        "filename": file_record.filename,
        "expires_in_seconds": 60
    }