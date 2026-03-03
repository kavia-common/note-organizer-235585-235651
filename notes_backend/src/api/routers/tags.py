from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.core.auth import get_current_user
from src.api.core.db import get_db
from src.api.models import Tag, User
from src.api.schemas import ApiMessage, TagCreate, TagResponse, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagResponse],
    summary="List tags",
    description="List all tags for the authenticated user.",
    operation_id="list_tags",
)
def list_tags(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TagResponse]:
    """List tags for the current user."""
    tags = db.execute(select(Tag).where(Tag.user_id == user.id).order_by(Tag.name.asc())).scalars().all()
    return [TagResponse(id=t.id, name=t.name, color=t.color, created_at=t.created_at) for t in tags]


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
    description="Create a new tag for the authenticated user.",
    operation_id="create_tag",
)
def create_tag(req: TagCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TagResponse:
    """Create a tag (name unique per user)."""
    tag = Tag(user_id=user.id, name=req.name.strip(), color=req.color)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tag name already exists") from e
    db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name, color=tag.color, created_at=tag.created_at)


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
    description="Update an existing tag (user-scoped).",
    operation_id="update_tag",
)
def update_tag(
    tag_id: str,
    req: TagUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagResponse:
    """Update a tag owned by the current user."""
    tag = db.get(Tag, tag_id)
    if not tag or tag.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tag not found")

    if req.name is not None:
        tag.name = req.name.strip()
    if req.color is not None:
        tag.color = req.color

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tag name already exists") from e
    db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name, color=tag.color, created_at=tag.created_at)


@router.delete(
    "/{tag_id}",
    response_model=ApiMessage,
    summary="Delete tag",
    description="Delete a tag owned by the current user.",
    operation_id="delete_tag",
)
def delete_tag(
    tag_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiMessage:
    """Delete a tag (also removes note associations via cascade)."""
    tag = db.get(Tag, tag_id)
    if not tag or tag.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return ApiMessage(message="Tag deleted")
