from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import get_folder_access_level, has_at_least, AccessLevel
from app.models.user import User
from app.models.folder import Folder
from app.models.file import File
from app.schemas.folder import (
    FolderCreate, FolderResponse, FolderContentsResponse,
    BreadcrumbItem, BreadcrumbResponse, FolderRename, FolderMove
)
from app.schemas.file import FileResponse

router = APIRouter(prefix="/folders", tags=["Folders"])


def _folder_response(f: Folder) -> FolderResponse:
    return FolderResponse(id=f.id, name=f.name, parent_id=f.parent_id, created_at=str(f.created_at))


@router.post("/", response_model=FolderResponse)
def create_folder(
    request: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.parent_id is not None:
        parent = db.query(Folder).filter(
            Folder.id == request.parent_id, Folder.is_deleted == False
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")

        access = get_folder_access_level(parent, current_user.id, db)
        if not has_at_least(access, AccessLevel.editor):
            raise HTTPException(status_code=404, detail="Parent folder not found")

    new_folder = Folder(name=request.name, owner_id=current_user.id, parent_id=request.parent_id)
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    return _folder_response(new_folder)


@router.get("/contents", response_model=FolderContentsResponse)
def get_folder_contents(
    folder_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if folder_id is not None:
        folder = db.query(Folder).filter(Folder.id == folder_id, Folder.is_deleted == False).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        access = get_folder_access_level(folder, current_user.id, db)
        if not has_at_least(access, AccessLevel.viewer):
            raise HTTPException(status_code=404, detail="Folder not found")

       
        subfolders = db.query(Folder).filter(
            Folder.parent_id == folder_id, Folder.is_deleted == False
        ).all()
        files_in_folder = db.query(File).filter(
            File.folder_id == folder_id, File.is_deleted == False
        ).all()
    else:
        
        subfolders = db.query(Folder).filter(
            Folder.parent_id == None, Folder.owner_id == current_user.id, Folder.is_deleted == False
        ).all()
        files_in_folder = db.query(File).filter(
            File.folder_id == None, File.owner_id == current_user.id, File.is_deleted == False
        ).all()

    return FolderContentsResponse(
        folders=[_folder_response(f) for f in subfolders],
        files=[
            FileResponse(id=f.id, filename=f.filename, file_type=f.file_type,
                          file_size=f.file_size, folder_id=f.folder_id, created_at=str(f.created_at))
            for f in files_in_folder
        ]
    )


@router.get("/{folder_id}/breadcrumbs", response_model=BreadcrumbResponse)
def get_breadcrumbs(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    path = []
    current_id = folder_id

    while current_id is not None:
        folder = db.query(Folder).filter(Folder.id == current_id, Folder.is_deleted == False).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        
        access = get_folder_access_level(folder, current_user.id, db)
        if not has_at_least(access, AccessLevel.viewer):
            raise HTTPException(status_code=404, detail="Folder not found")

        path.append(BreadcrumbItem(id=folder.id, name=folder.name))
        current_id = folder.parent_id

    path.reverse()
    return BreadcrumbResponse(path=path)


@router.patch("/{folder_id}/rename", response_model=FolderResponse)
def rename_folder(
    folder_id: int,
    request: FolderRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.is_deleted == False).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    access = get_folder_access_level(folder, current_user.id, db)
    if not has_at_least(access, AccessLevel.editor):
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.name = request.name
    db.commit()
    db.refresh(folder)
    return _folder_response(folder)


@router.patch("/{folder_id}/move", response_model=FolderResponse)
def move_folder(
    folder_id: int,
    request: FolderMove,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.is_deleted == False).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Moving is Owner-only - reorganizing someone else's folder tree is too risky for Editors
    access = get_folder_access_level(folder, current_user.id, db)
    if not has_at_least(access, AccessLevel.owner):
        raise HTTPException(status_code=404, detail="Folder not found")

    new_parent_id = request.parent_id

    if new_parent_id is not None:
        if new_parent_id == folder_id:
            raise HTTPException(status_code=400, detail="Cannot move a folder into itself")

        destination = db.query(Folder).filter(
            Folder.id == new_parent_id, Folder.owner_id == current_user.id, Folder.is_deleted == False
        ).first()
        if not destination:
            raise HTTPException(status_code=404, detail="Destination folder not found")

        current_id = destination.parent_id
        while current_id is not None:
            if current_id == folder_id:
                raise HTTPException(status_code=400, detail="Cannot move a folder into its own subfolder")
            parent = db.query(Folder).filter(Folder.id == current_id).first()
            current_id = parent.parent_id if parent else None

    folder.parent_id = new_parent_id
    db.commit()
    db.refresh(folder)
    return _folder_response(folder)


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.is_deleted == False).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    access = get_folder_access_level(folder, current_user.id, db)
    if not has_at_least(access, AccessLevel.owner):
        raise HTTPException(status_code=404, detail="Folder not found")

    _cascade_delete_folder(folder_id, folder.owner_id, db)
    db.commit()
    return {"message": "Folder moved to trash", "id": folder_id}


def _cascade_delete_folder(folder_id: int, owner_id: int, db: Session):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    folder.is_deleted = True

    files_inside = db.query(File).filter(File.folder_id == folder_id, File.owner_id == owner_id).all()
    for f in files_inside:
        f.is_deleted = True

    subfolders = db.query(Folder).filter(Folder.parent_id == folder_id, Folder.owner_id == owner_id).all()
    for sub in subfolders:
        _cascade_delete_folder(sub.id, owner_id, db)