from email.policy import HTTP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.folder import Folder
from app.models.share import Share
from app.schemas.share import ShareCreate, ShareResponse, SharedFileItem, SharedFolderItem, SharedWithMeResponse, ShareListItem, ShareListResponse, ShareUpdateRole
from app.schemas.file import FileResponse
from app.schemas.folder import FolderResponse

router=APIRouter(prefix="/shares",tags=["Sharing"])

@router.post("/",response_model=ShareResponse)
def create_share(
    request: ShareCreate,
    current_user: User=Depends(get_current_user),
    db: Session=Depends(get_db)
):
    if(request.file_id is None)==(request.folder_id is None):
        raise HTTPException(status_code=400, detail="Provide exactly one of file_id or folder_id")
    
    if request.file_id is not None:
        item=db.query(File).filter(
            File.id==request.file_id,
            File.owner_id==current_user.id,
            File.is_deleted==False
        ).first()
        item_type="file"
    else:
        item=db.query(Folder).filter(
            Folder.id==request.folder_id,
            Folder.owner_id==current_user.id,
            Folder.is_deleted==False
        ).first()
        item_type="folder"
        
    if not item:
        raise HTTPException(status_code=404, detail=f"{item_type.capitalize()} not found")
    
    target_user=db.query(User).filter(User.email==request.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="No user found with that email")
    
    if target_user.id==current_user.id:
        raise HTTPException(status_code=400, detail="You cannot share with yourself")
    
    existing_share_query=db.query(Share).filter(
        Share.shared_with_user_id==target_user.id
    )
    
    if request.file_id is not None:
        existing_share_query=existing_share_query.filter(Share.file_id==request.file_id)
    else:
        existing_share_query=existing_share_query.filter(Share.folder_id==request.folder_id)
    
    existing_share=existing_share_query.first()
    
    if existing_share:
        existing_share.role=request.role
        db.commit()
        db.refresh(existing_share)
        result_share=existing_share
    else:
        new_share=Share(
            file_id=request.file_id,
            folder_id=request.folder_id,
            shared_with_user_id=target_user.id,
            shared_by_user_id=current_user.id,
            role=request.role
        )
        db.add(new_share)
        db.commit()
        db.refresh(new_share)
        result_share=new_share
        
    return ShareResponse(
        id=result_share.id,
        file_id=result_share.file_id,
        folder_id=result_share.folder_id,
        shared_with_user_id=result_share.shared_with_user_id,
        shared_with_email=target_user.email,
        role=result_share.role,
        created_at=str(result_share.created_at)
    )
    
@router.get("/shared-with-me", response_model=SharedWithMeResponse)
def get_shared_with_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    my_shares = db.query(Share).filter(Share.shared_with_user_id == current_user.id).all()

    shared_files = []
    shared_folders = []

    for share in my_shares:
        owner = db.query(User).filter(User.id == share.shared_by_user_id).first()

        if share.file_id is not None:
            file_record = db.query(File).filter(
                File.id == share.file_id, File.is_deleted == False
            ).first()

            if file_record:  
                shared_files.append(SharedFileItem(
                    share_id=share.id,
                    role=share.role,
                    owner_email=owner.email,
                    file=FileResponse(
                        id=file_record.id, filename=file_record.filename, file_type=file_record.file_type,
                        file_size=file_record.file_size, folder_id=file_record.folder_id,
                        created_at=str(file_record.created_at)
                    )
                ))

        elif share.folder_id is not None:
            folder_record = db.query(Folder).filter(
                Folder.id == share.folder_id, Folder.is_deleted == False
            ).first()

            if folder_record:
                shared_folders.append(SharedFolderItem(
                    share_id=share.id,
                    role=share.role,
                    owner_email=owner.email,
                    folder=FolderResponse(
                        id=folder_record.id, name=folder_record.name,
                        parent_id=folder_record.parent_id, created_at=str(folder_record.created_at)
                    )
                ))

    return SharedWithMeResponse(files=shared_files, folders=shared_folders)   

@router.get("/for-item", response_model=ShareListResponse)
def list_shares_for_item(
    file_id: int = None,
    folder_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if (file_id is None) == (folder_id is None):
        raise HTTPException(status_code=400, detail="Provide exactly one of file_id or folder_id")

 
    if file_id is not None:
        item = db.query(File).filter(
            File.id == file_id, File.owner_id == current_user.id, File.is_deleted == False
        ).first()
    else:
        item = db.query(Folder).filter(
            Folder.id == folder_id, Folder.owner_id == current_user.id, Folder.is_deleted == False
        ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    query = db.query(Share)
    query = query.filter(Share.file_id == file_id) if file_id is not None else query.filter(Share.folder_id == folder_id)
    shares = query.all()

    result = []
    for share in shares:
        recipient = db.query(User).filter(User.id == share.shared_with_user_id).first()
        result.append(ShareListItem(
            share_id=share.id,
            shared_with_email=recipient.email,
            role=share.role,
            created_at=str(share.created_at)
        ))

    return ShareListResponse(shares=result)


@router.patch("/{share_id}", response_model=ShareResponse)
def update_share_role(
    share_id: int,
    request: ShareUpdateRole,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    share = db.query(Share).filter(Share.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    owner_id = _get_owner_id_for_share(share, db)
    if owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Share not found")

    share.role = request.role
    db.commit()
    db.refresh(share)

    recipient = db.query(User).filter(User.id == share.shared_with_user_id).first()

    return ShareResponse(
        id=share.id, file_id=share.file_id, folder_id=share.folder_id,
        shared_with_user_id=share.shared_with_user_id, shared_with_email=recipient.email,
        role=share.role, created_at=str(share.created_at)
    )


@router.delete("/{share_id}")
def delete_share(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    share = db.query(Share).filter(Share.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    owner_id = _get_owner_id_for_share(share, db)
    if owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Share not found")

    db.delete(share)
    db.commit()

    return {"message": "Access removed", "share_id": share_id}


def _get_owner_id_for_share(share: Share, db: Session):
    if share.file_id is not None:
        file_record = db.query(File).filter(File.id == share.file_id).first()
        return file_record.owner_id if file_record else None
    else:
        folder_record = db.query(Folder).filter(Folder.id == share.folder_id).first()
        return folder_record.owner_id if folder_record else None
            