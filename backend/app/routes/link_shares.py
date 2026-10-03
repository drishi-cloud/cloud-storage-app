import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.supabase_client import supabase, SUPABASE_BUCKET_NAME
from app.core.permissions import get_file_access_level, has_at_least, AccessLevel
from app.models.user import User
from app.models.file import File
from app.models.link_share import LinkShare
from app.schemas.link_share import LinkShareCreate, LinkShareResponse, PublicFileInfo

router = APIRouter(prefix="/link-shares", tags=["Public Links"])


@router.post("/", response_model=LinkShareResponse)
def create_link_share(
    request: LinkShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(
        File.id == request.file_id, File.is_deleted == False
    ).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Creating a public link is Owner-only - sharing out this broadly is a bigger decision
    access = get_file_access_level(file_record, current_user.id, db)
    if not has_at_least(access, AccessLevel.owner):
        raise HTTPException(status_code=404, detail="File not found")

    token = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_in_hours)

    new_link = LinkShare(
        token=token,
        file_id=file_record.id,
        created_by_user_id=current_user.id,
        expires_at=expires_at
    )

    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return LinkShareResponse(token=new_link.token, expires_at=str(new_link.expires_at))


@router.get("/{token}", response_model=PublicFileInfo)
def access_public_link(token: str, db: Session = Depends(get_db)):
    # Notice: NO get_current_user dependency here - this endpoint is intentionally public,
    # anyone with the token can call it, logged in or not.

    link = db.query(LinkShare).filter(LinkShare.token == token).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.is_revoked:
        raise HTTPException(status_code=410, detail="This link has been revoked")

    if datetime.now(timezone.utc) > link.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=410, detail="This link has expired")

    file_record = db.query(File).filter(
        File.id == link.file_id, File.is_deleted == False
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File no longer available")

    try:
        signed_response = supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_url(
            file_record.storage_key, 60
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate download URL: {str(e)}")

    return PublicFileInfo(
        filename=file_record.filename,
        file_type=file_record.file_type,
        file_size=file_record.file_size,
        download_url=signed_response["signedURL"]
    )


@router.delete("/{token}")
def revoke_link_share(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    link = db.query(LinkShare).filter(LinkShare.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Link not found")

    link.is_revoked = True
    db.commit()

    return {"message": "Link revoked", "token": token}