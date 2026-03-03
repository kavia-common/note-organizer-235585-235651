from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session, joinedload

from src.api.core.auth import get_current_user
from src.api.core.db import get_db
from src.api.models import Note, Tag, User
from src.api.schemas import ApiMessage, NoteCreate, NoteResponse, NoteUpdate, NotesListResponse, TagResponse

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_to_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        content_format=note.content_format,
        is_archived=note.is_archived,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[
            TagResponse(id=t.id, name=t.name, color=t.color, created_at=t.created_at)
            for t in sorted(note.tags, key=lambda x: x.name.lower())
        ],
    )


def _set_note_tags(db: Session, user: User, note: Note, tag_ids: list[UUID]) -> None:
    # Ensure tags exist and belong to user
    if not tag_ids:
        note.tags = []
        return

    tags = db.execute(select(Tag).where(and_(Tag.user_id == user.id, Tag.id.in_(tag_ids)))).scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tag_ids are invalid")
    note.tags = tags


@router.get(
    "",
    response_model=NotesListResponse,
    summary="List notes",
    description="List notes for the authenticated user (optionally filter by archived or tag).",
    operation_id="list_notes",
)
def list_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    archived: bool | None = Query(None, description="Filter by archived status."),
    tag_id: UUID | None = Query(None, description="Filter notes that have a specific tag."),
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
) -> NotesListResponse:
    """List notes for current user with filters."""
    filters = [Note.user_id == user.id]
    if archived is not None:
        filters.append(Note.is_archived == archived)

    stmt = (
        select(Note)
        .where(and_(*filters))
        .options(joinedload(Note.tags))
        .order_by(Note.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if tag_id is not None:
        # join through association table via relationship
        stmt = stmt.join(Note.tags).where(Tag.id == tag_id)

    items = db.execute(stmt).unique().scalars().all()

    # Total count
    count_stmt = select(func.count(Note.id)).where(and_(*filters))
    if tag_id is not None:
        count_stmt = count_stmt.select_from(Note).join(Note.tags).where(Tag.id == tag_id)
    total = db.execute(count_stmt).scalar_one()

    return NotesListResponse(items=[_note_to_response(n) for n in items], total=int(total))


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create note",
    description="Create a note for the authenticated user.",
    operation_id="create_note",
)
def create_note(
    req: NoteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Create a note and optionally attach tags."""
    note = Note(
        user_id=user.id,
        title=req.title,
        content=req.content,
        content_format=req.content_format,
        is_archived=False,
    )
    db.add(note)
    db.flush()  # ensure note.id exists before tag association

    _set_note_tags(db, user, note, req.tag_ids)

    db.commit()
    db.refresh(note)
    return _note_to_response(note)


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get note",
    description="Get a single note by id (user-scoped).",
    operation_id="get_note",
)
def get_note(note_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> NoteResponse:
    """Get one note owned by the current user."""
    note = (
        db.execute(select(Note).where(and_(Note.id == note_id, Note.user_id == user.id)).options(joinedload(Note.tags)))
        .unique()
        .scalar_one_or_none()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _note_to_response(note)


@router.patch(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Update note",
    description="Update a note (user-scoped). If tag_ids is provided, replaces tag set.",
    operation_id="update_note",
)
def update_note(
    note_id: UUID,
    req: NoteUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Update a note and optionally replace its tags."""
    note = (
        db.execute(select(Note).where(and_(Note.id == note_id, Note.user_id == user.id)).options(joinedload(Note.tags)))
        .unique()
        .scalar_one_or_none()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if req.title is not None:
        note.title = req.title
    if req.content is not None:
        note.content = req.content
    if req.content_format is not None:
        note.content_format = req.content_format
    if req.is_archived is not None:
        note.is_archived = req.is_archived
    if req.tag_ids is not None:
        _set_note_tags(db, user, note, req.tag_ids)

    db.commit()
    db.refresh(note)
    return _note_to_response(note)


@router.delete(
    "/{note_id}",
    response_model=ApiMessage,
    summary="Delete note",
    description="Delete a note (user-scoped).",
    operation_id="delete_note",
)
def delete_note(note_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiMessage:
    """Delete a note owned by the current user."""
    note = db.execute(select(Note).where(and_(Note.id == note_id, Note.user_id == user.id))).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return ApiMessage(message="Note deleted")


@router.get(
    "/search",
    response_model=NotesListResponse,
    summary="Search notes",
    description="Search notes by a query string using Postgres full-text search on the stored search_vector.",
    operation_id="search_notes",
)
def search_notes(
    q: str = Query(..., min_length=1, description="Search query."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
) -> NotesListResponse:
    """
    Full-text search using `notes.search_vector` generated column.

    This relies on the DB schema from notes_database/README_schema_and_seed.md.
    """
    # Use plainto_tsquery for simple user input.
    stmt = (
        select(Note)
        .where(Note.user_id == user.id)
        .where(text("notes.search_vector @@ plainto_tsquery('english', :q)"))
        .params(q=q)
        .options(joinedload(Note.tags))
        .order_by(Note.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = db.execute(stmt).unique().scalars().all()

    count_stmt = (
        select(func.count(Note.id))
        .where(Note.user_id == user.id)
        .where(text("notes.search_vector @@ plainto_tsquery('english', :q)"))
        .params(q=q)
    )
    total = db.execute(count_stmt).scalar_one()

    return NotesListResponse(items=[_note_to_response(n) for n in items], total=int(total))
